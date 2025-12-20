import { useState, useEffect, useCallback, useRef } from 'react';

// MCP 服务器地址
const MCP_SERVER = 'http://localhost:8080';

// 工具类型定义
interface Tool {
  description: string;
  parameters: Record<string, any>;
}

interface Document {
  name: string;
  path: string;
  size: number;
  modified: string;
}

interface SSEMessage {
  type: 'connected' | 'tools' | 'heartbeat' | 'start' | 'result' | 'done' | 'error' | 'progress';
  message?: string;
  tools?: string[];
  data?: any;
  error?: string;
  time?: string;
  tool?: string;
  step?: number;
  label?: string;
}

// 消息类型：用户消息、助手回复、系统日志
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  logType?: 'info' | 'success' | 'error' | 'working';
}

// 主组件
export default function WordMCPClient() {
  const [connected, setConnected] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [tools, setTools] = useState<Record<string, Tool>>({});
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState('');

  const eventSourceRef = useRef<EventSource | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动消息到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 添加消息（支持用户、助手、系统日志）
  const addMessage = useCallback((
    role: 'user' | 'assistant' | 'system',
    content: string,
    logType?: 'info' | 'success' | 'error' | 'working'
  ) => {
    setMessages(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      role,
      content,
      timestamp: new Date(),
      logType
    }]);
  }, []);

  // 添加系统日志（显示在对话中）
  const addLog = useCallback((message: string, type: 'info' | 'success' | 'error' | 'working' = 'info') => {
    addMessage('system', message, type);
  }, [addMessage]);

  // 清除最后一个 working 状态的日志（每个步骤完成时调用）
  const clearLastWorkingLog = useCallback(() => {
    setMessages(prev => {
      // 从后往前找到最后一个 working 日志并移除
      const lastWorkingIndex = prev.map((msg, i) => ({ msg, i }))
        .reverse()
        .find(({ msg }) => msg.role === 'system' && msg.logType === 'working')?.i;
      
      if (lastWorkingIndex !== undefined) {
        return prev.filter((_, i) => i !== lastWorkingIndex);
      }
      return prev;
    });
  }, []);

  // 清除所有 working 状态的日志
  const clearAllWorkingLogs = useCallback(() => {
    setMessages(prev => prev.filter(msg => !(msg.role === 'system' && msg.logType === 'working')));
  }, []);

  // 建立 SSE 连接
  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`${MCP_SERVER}/sse`);

    es.onopen = () => {
      setConnected(true);
    };

    es.onmessage = (event) => {
      try {
        const data: SSEMessage = JSON.parse(event.data);
        switch (data.type) {
          case 'connected':
            // 静默处理
            break;
          case 'tools':
            // 静默处理
            break;
          case 'heartbeat':
            break;
        }
      } catch (e) {
        console.error('解析 SSE 消息失败:', e);
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
    };

    eventSourceRef.current = es;
  }, []);

  // 获取工具列表
  const fetchTools = useCallback(async () => {
    try {
      const res = await fetch(`${MCP_SERVER}/tools`);
      const data = await res.json();
      setTools(data.tools || {});
    } catch (e) {
      // 静默处理
    }
  }, []);

  // 获取文档列表
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${MCP_SERVER}/documents`);
      const data = await res.json();
      if (data.success) {
        setDocuments(data.documents || []);
      }
    } catch (e) {
      // 静默处理
    }
  }, []);

  // 调用工具 (SSE 方式)
  const callTool = useCallback(async (tool: string, params: Record<string, any>) => {
    setLoading(true);
    
    // 显示正在执行的工具
    const toolNames: Record<string, string> = {
      'list_documents': '列出文档',
      'read_document': '读取文档',
      'create_document': '创建文档',
      'update_document': '更新文档',
      'add_table': '添加表格',
      'search_replace': '搜索替换',
      'delete_document': '删除文档'
    };
    addLog(`正在调用工具: ${toolNames[tool] || tool}`, 'working');

    try {
      const url = `${MCP_SERVER}/sse/call`;
      const requestBody = { tool, params };
      
      console.log('[WordMCP] 发送请求:', { url, tool, params });
      
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      console.log('[WordMCP] 响应状态:', res.status, res.statusText);

      // 检查 HTTP 响应状态
      if (!res.ok) {
        const errorText = await res.text();
        console.error('[WordMCP] 请求失败:', res.status, errorText);
        throw new Error(`服务器错误: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ''}`);
      }

      // 检查响应类型
      const contentType = res.headers.get('content-type');
      if (!contentType || !contentType.includes('text/event-stream')) {
        console.warn('[WordMCP] 意外的响应类型:', contentType);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('无法读取响应流');
      }

      let resultContent = '';
      let currentToolName = tool; // 保存工具名称用于格式化结果（支持后端多步 start 里切换）

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6);
              console.log('[WordMCP] 收到 SSE 数据:', jsonStr);
              const data: SSEMessage = JSON.parse(jsonStr);
              console.log('[WordMCP] 解析后的数据:', data);

              switch (data.type) {
                case 'start':
                  if (data.tool) currentToolName = data.tool;
                  addLog(data.label ? `开始：${data.label}` : '开始执行...', 'info');
                  break;
                case 'progress':
                  if (data.message) addLog(data.message, 'working');
                  break;
                case 'result':
                  if (data.data?.success) {
                    addLog('执行成功', 'success');
                    
                    // 根据不同工具类型，格式化显示结果
                    const toolName = currentToolName;
                    const appendResult = (text: string) => {
                      resultContent = resultContent
                        ? `${resultContent}\n\n---\n\n${text}`
                        : text;
                    };
                    if (toolName === 'create_document') {
                      // 创建文档：显示文件名和路径
                      const filePath = data.data?.file_path || '';
                      const fileName = filePath.split('/').pop() || filePath.split('\\').pop() || '未知文件';
                      appendResult(`✅ 文档创建成功！\n\n文件名：${fileName}\n路径：${filePath}${data.data?.file_size ? `\n大小：${(data.data.file_size / 1024).toFixed(2)} KB` : ''}`);
                    } else if (toolName === 'list_documents') {
                      // 列出文档：格式化显示文档列表
                      const docs = data.data?.documents || [];
                      if (docs.length === 0) {
                        appendResult('📋 当前没有文档');
                      } else {
                        appendResult(`📋 共找到 ${docs.length} 个文档：\n\n${docs.map((doc: any, index: number) => 
                          `${index + 1}. ${doc.name} (${(doc.size / 1024).toFixed(2)} KB)`
                        ).join('\n')}`);
                      }
                    } else if (toolName === 'read_document') {
                      // 读取文档：显示文档内容
                      const fullText = data.data?.full_text || '';
                      const paragraphs = data.data?.paragraphs || [];
                      if (fullText) {
                        appendResult(`📖 文档内容：\n\n${fullText}`);
                      } else if (paragraphs.length > 0) {
                        appendResult(`📖 文档内容：\n\n${paragraphs.join('\n\n')}`);
                      } else {
                        appendResult(data.data?.message || '文档读取成功，但内容为空');
                      }
                    } else if (toolName === 'delete_document') {
                      appendResult(`✅ ${data.data?.message || '文档删除成功'}`);
                    } else if (toolName === 'update_document') {
                      appendResult(`✅ ${data.data?.message || '文档更新成功'}`);
                    } else if (toolName === 'add_table') {
                      appendResult(`✅ ${data.data?.message || '表格添加成功'}`);
                    } else {
                      appendResult(data.data?.message || JSON.stringify(data.data, null, 2));
                    }
                  } else {
                    addLog(`执行失败: ${data.data?.error || '未知错误'}`, 'error');
                    resultContent = `❌ 错误：${data.data?.error || '未知错误'}`;
                  }
                  break;
                case 'error':
                  addLog(`错误: ${data.error}`, 'error');
                  resultContent = `❌ 错误：${data.error}`;
                  break;
                case 'done':
                  console.log('[WordMCP] 执行完成');
                  break;
              }
            } catch (e) {
              console.error('[WordMCP] 解析 SSE 数据失败:', e, '原始行:', line);
            }
          }
        }
      }

      if (resultContent) {
        addMessage('assistant', resultContent);
      }

      await fetchDocuments();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      console.error('[WordMCP] 调用工具失败:', e);
      addLog(`调用失败: ${errorMsg}`, 'error');
      addMessage('assistant', `抱歉，执行出错: ${errorMsg}`);
    } finally {
      // 清除所有剩余的 working 状态日志
      clearAllWorkingLogs();
      setLoading(false);
    }
  }, [addLog, addMessage, fetchDocuments, clearAllWorkingLogs]);

  // 多步编排（真·SSE）- 支持 LLM Agent 的完整流程
  const callAgent = useCallback(async (payload: { query: string; title?: string; filename?: string }) => {
    setLoading(true);

    try {
      const url = `${MCP_SERVER}/sse/agent`;
      console.log('[WordMCP] 发送 Agent 请求:', { url, payload });

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      console.log('[WordMCP] Agent 响应状态:', res.status, res.statusText);

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`服务器错误: ${res.status} ${res.statusText}${errorText ? ` - ${errorText}` : ''}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('无法读取响应流');

      let lastCreatedFilePath = '';
      let finalResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6);
          console.log('[WordMCP] 收到 Agent SSE 数据:', jsonStr);

          let data: any;
          try {
            data = JSON.parse(jsonStr);
          } catch (e) {
            console.error('[WordMCP] 解析 Agent SSE 失败:', e, '原始行:', line);
            continue;
          }

          // 工具名称映射
          const toolNames: Record<string, string> = {
            'create_document': '创建文档',
            'read_document': '读取文档',
            'update_document': '更新文档',
            'delete_document': '删除文档',
            'list_documents': '列出文档',
            'add_table': '添加表格',
            'search_replace': '搜索替换'
          };

          // 处理不同类型的 SSE 消息
          switch (data.type) {
            case 'start':
              addLog(data.message || '开始执行...', 'info');
              break;

            case 'thinking':
              addLog(data.message || '正在思考...', 'working');
              break;

            case 'tool_call':
              // 先清除上一个 working 日志（如 thinking）
              clearLastWorkingLog();
              // 显示正在调用的工具
              addLog(`🔧 调用工具: ${toolNames[data.tool] || data.tool}`, 'working');
              
              // 显示工具参数摘要
              if (data.arguments) {
                const args = data.arguments;
                if (args.title) {
                  addLog(`  📝 标题: ${args.title}`, 'info');
                }
                if (args.filename) {
                  addLog(`  📄 文件: ${args.filename}`, 'info');
                }
              }
              break;

            case 'tool_result':
              // 先清除上一个 working 日志（如 tool_call）
              clearLastWorkingLog();
              if (data.result?.success) {
                addLog(`✅ ${toolNames[data.tool] || data.tool} 成功`, 'success');
                
                // 记录创建的文件路径
                if (data.result?.file_path) {
                  lastCreatedFilePath = data.result.file_path;
                  addLog(`  📁 文件: ${data.result.file_path}`, 'info');
                }
              } else {
                addLog(`❌ ${data.tool} 失败: ${data.result?.error || '未知错误'}`, 'error');
              }
              break;

            case 'response':
              // 先清除上一个 working 日志
              clearLastWorkingLog();
              // LLM 的最终回复
              if (data.content) {
                finalResponse = data.content;
              }
              break;

            case 'error':
              clearLastWorkingLog();
              addLog(`❌ 错误: ${data.error}`, 'error');
              addMessage('assistant', `❌ 错误：${data.error}`);
              break;

            case 'warning':
              addLog(`⚠️ ${data.message}`, 'info');
              break;

            case 'done':
              // 清除所有剩余的 working 日志
              clearAllWorkingLogs();
              break;

            case 'progress':
              if (data.message) addLog(data.message, 'working');
              break;

            case 'result':
              // 旧格式兼容
              clearLastWorkingLog();
              if (data.data?.success) {
                addLog('执行成功', 'success');
                if (data.data?.file_path) lastCreatedFilePath = data.data.file_path;
              }
              break;
          }
        }
      }

      // 显示最终结果
      if (finalResponse) {
        addMessage('assistant', finalResponse);
      } else if (lastCreatedFilePath) {
        addMessage('assistant', `✅ 文档已创建！\n\n📁 文件路径: ${lastCreatedFilePath}`);
      }

      await fetchDocuments();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      console.error('[WordMCP] Agent 调用失败:', e);
      addLog(`调用失败: ${errorMsg}`, 'error');
      addMessage('assistant', `抱歉，执行出错: ${errorMsg}`);
    } finally {
      // 清除所有剩余的 working 状态日志
      clearAllWorkingLogs();
      setLoading(false);
    }
  }, [addLog, addMessage, fetchDocuments, clearLastWorkingLog, clearAllWorkingLogs]);

  // 处理聊天输入 - 全部交给 LLM Agent 处理
  const handleChat = async () => {
    if (!userInput.trim() || loading) return;

    const query = userInput.trim();
    setUserInput('');
    addMessage('user', query);

    console.log('[WordMCP] 交给 LLM Agent 处理:', query);
    
    // 直接交给 LLM Agent，让它决定调用哪些工具
    await callAgent({ query });
  };

  // 初始化
  useEffect(() => {
    connectSSE();
    fetchTools();
    fetchDocuments();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [connectSSE, fetchTools, fetchDocuments]);

  // 渲染消息
  const renderMessage = (msg: Message) => {
    // 系统日志消息
    if (msg.role === 'system') {
      const icons: Record<string, string> = {
        info: '○',
        success: '✓',
        error: '✗',
        working: '◎'
      };
      const colors: Record<string, string> = {
        info: '#6b7280',
        success: '#10b981',
        error: '#ef4444',
        working: '#f59e0b'
      };
      
      return (
        <div key={msg.id} style={styles.systemMessage}>
          <span style={{ 
            ...styles.systemIcon, 
            color: colors[msg.logType || 'info'],
            animation: msg.logType === 'working' ? 'pulse 1.5s infinite' : 'none'
          }}>
            {icons[msg.logType || 'info']}
          </span>
          <span style={{ ...styles.systemText, color: colors[msg.logType || 'info'] }}>
            {msg.content}
          </span>
        </div>
      );
    }

    // 用户/助手消息
    return (
      <div
        key={msg.id}
        style={{
          ...styles.messageRow,
          justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
        }}
      >
        <div
          style={{
            ...styles.messageBubble,
            ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble)
          }}
        >
          <div style={styles.messageContent}>{msg.content}</div>
        </div>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      {/* 主内容区 */}
      <div style={styles.main}>
        {/* 头部标题 */}
        <div style={styles.header}>
          <h1 style={styles.title}>Word Agent</h1>
          <div style={styles.status}>
            <span style={{
              ...styles.statusDot,
              backgroundColor: connected ? '#10b981' : '#ef4444',
              boxShadow: connected ? '0 0 8px #10b981' : '0 0 8px #ef4444'
            }} />
            <span style={styles.statusText}>{connected ? '已连接' : '未连接'}</span>
          </div>
        </div>

        {/* 对话区域 */}
        <div style={styles.chatContainer}>
          <div style={styles.messagesWrapper} className="messages-scroll">
            {messages.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyIcon}>📄</div>
                <p style={styles.emptyTitle}>Word 文档助手</p>
                <p style={styles.emptySubtitle}>输入指令来管理你的 Word 文档</p>
                <div style={styles.suggestions}>
                  {[
                    { label: '📋 列出文档', cmd: '列出该目录下有哪些文档' },
                    { label: '📝 创建文档', cmd: '创建文档' },
                    { label: '📖 读取文档', cmd: '读取文档' }
                  ].map(({ label, cmd }) => (
                    <button
                      key={cmd}
                      onClick={() => setUserInput(cmd)}
                      style={styles.suggestionBtn}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={styles.messagesList}>
                {messages.map(renderMessage)}
                {/* {loading && (
                  <div style={styles.systemMessage}>
                    <span style={{ ...styles.systemIcon, color: '#f59e0b', animation: 'pulse 1.5s infinite' }}>◎</span>
                    <span style={{ ...styles.systemText, color: '#f59e0b' }}>思考中...</span>
                  </div>
                )} */}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* 输入框 */}
          <div style={styles.inputWrapper}>
            <div style={styles.inputContainer}>
              <textarea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleChat();
                  }
                }}
                placeholder="输入指令..."
                style={styles.textarea}
                rows={1}
              />
              <button
                onClick={handleChat}
                disabled={!userInput.trim() || loading}
                style={{
                  ...styles.sendBtn,
                  opacity: (!userInput.trim() || loading) ? 0.5 : 1,
                  cursor: (!userInput.trim() || loading) ? 'not-allowed' : 'pointer'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 全局样式 */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes typing {
          0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
          30% { opacity: 1; transform: translateY(-4px); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        
        .messages-scroll::-webkit-scrollbar {
          width: 6px;
        }
        .messages-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
        .messages-scroll::-webkit-scrollbar-thumb {
          background: #374151;
          border-radius: 6px;
        }
        
        textarea:focus {
          outline: none;
        }
        
        button:hover:not(:disabled) {
          filter: brightness(1.1);
        }
      `}} />
    </div>
  );
}

// 样式定义
const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100dvh',
    backgroundColor: '#212121',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  
  main: {
    width: '100%',
    maxWidth: '680px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 4px',
  },
  
  title: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#ffffff',
    margin: 0,
    letterSpacing: '-0.02em',
  },
  
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  
  statusText: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  
  chatContainer: {
    backgroundColor: '#2f2f2f',
    borderRadius: '16px',
    border: '1px solid #424242',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  
  messagesWrapper: {
    height: '520px',
    overflowY: 'auto',
    padding: '24px',
  },
  
  emptyState: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
  },
  
  emptyIcon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  
  emptyTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#ffffff',
    margin: '0 0 8px 0',
  },
  
  emptySubtitle: {
    fontSize: '14px',
    color: '#9ca3af',
    margin: '0 0 24px 0',
  },
  
  suggestions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    justifyContent: 'center',
  },
  
  suggestionBtn: {
    padding: '8px 16px',
    fontSize: '13px',
    color: '#d1d5db',
    backgroundColor: '#424242',
    border: '1px solid #525252',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  
  messagesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  
  messageRow: {
    display: 'flex',
    width: '100%',
  },
  
  messageBubble: {
    maxWidth: '85%',
    padding: '12px 16px',
    borderRadius: '18px',
    fontSize: '14px',
    lineHeight: 1.5,
  },
  
  userBubble: {
    backgroundColor: '#10a37f',
    color: '#ffffff',
    borderBottomRightRadius: '4px',
  },
  
  assistantBubble: {
    backgroundColor: '#424242',
    color: '#ececec',
    borderBottomLeftRadius: '4px',
  },
  
  messageContent: {
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  
  // 系统日志样式
  systemMessage: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    marginLeft: '8px',
  },
  
  systemIcon: {
    fontSize: '12px',
    fontWeight: 700,
  },
  
  systemText: {
    fontSize: '12px',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
  },
  
  inputWrapper: {
    padding: '16px',
    borderTop: '1px solid #424242',
    backgroundColor: '#2f2f2f',
  },
  
  inputContainer: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '12px',
    backgroundColor: '#424242',
    borderRadius: '12px',
    padding: '12px 16px',
    border: '1px solid #525252',
  },
  
  textarea: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    color: '#ffffff',
    fontSize: '14px',
    lineHeight: 1.5,
    resize: 'none',
    minHeight: '24px',
    maxHeight: '120px',
  },
  
  sendBtn: {
    width: '36px',
    height: '36px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#10a37f',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    transition: 'all 0.15s',
    flexShrink: 0,
  },
};
