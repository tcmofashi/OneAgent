<script setup>
import { ref, watch, onUnmounted, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps(['sessionId'])
const emit = defineEmits(['session-created'])

const messages = ref([])
const inputValue = ref('')
const isSending = ref(false)
const socket = ref(null)
const thoughtBuffer = ref([]) // For current streaming thoughts
const answerBuffer = ref('')  // For current streaming answer

const md = new MarkdownIt()

// Helpers
const scrollToBottom = () => {
    nextTick(() => {
        const container = document.querySelector('.messages-container')
        if (container) container.scrollTop = container.scrollHeight
    })
}

const isConnecting = ref(false)
const connectionError = ref(null)

const connectWebSocket = (sid) => {
    if (socket.value) {
        socket.value.close()
        socket.value = null
    }
    
    isConnecting.value = true
    connectionError.value = null
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${sid}`
    
    console.log(`[ChatBox] Attempting connection to: ${wsUrl}`)
    
    const ws = new WebSocket(wsUrl)
    socket.value = ws
    
    ws.addEventListener('open', (event) => {
        console.log("[ChatBox] WS Connected successfully", event)
        isConnecting.value = false
        // Flush any pending message if needed, or just let user type
    })
    
    ws.addEventListener('message', (event) => {
        // console.log("[ChatBox] WS Message received", event.data) // Too verbose for data
        try {
            const data = JSON.parse(event.data)
            handleEvent(data)
        } catch (e) {
            console.error("[ChatBox] Failed to parse WS message", e)
        }
    })
    
    ws.addEventListener('error', (err) => {
        console.error("[ChatBox] WS Error Event:", err)
        isConnecting.value = false
        connectionError.value = "Connection Failed"
    })
    
    ws.addEventListener('close', (event) => {
        console.log(`[ChatBox] WS Closed. Code: ${event.code}, Reason: ${event.reason}, Clean: ${event.wasClean}`)
        if (socket.value === ws) {
            socket.value = null
            isConnecting.value = false
        }
    })
}

const handleEvent = (event) => {
    console.log('[ChatBox] handleEvent:', event.type)
    if (event.type === 'input_ack') {
        // User input confirmed
    } else if (event.type === 'thought') {
        thoughtBuffer.value.push({ type: 'thought', content: event.content })
        scrollToBottom()
    } else if (event.type === 'tool_call') {
        thoughtBuffer.value.push({ type: 'tool_call', name: event.name, args: event.args })
        scrollToBottom()
    } else if (event.type === 'tool_result') {
        thoughtBuffer.value.push({ type: 'tool_result', name: event.name, result: event.result })
        scrollToBottom()
    } else if (event.type === 'answer_chunk') {
        answerBuffer.value += event.content
        scrollToBottom()
    } else if (event.type === 'answer_done') {
        // Finalize message
        messages.value.push({
            role: 'assistant',
            content: event.content, // Use final content or buffer
            thoughts: [...thoughtBuffer.value]
        })
        isSending.value = false
        // Reset buffers
        thoughtBuffer.value = []
        answerBuffer.value = ''
        scrollToBottom()
    } else if (event.type === 'error') {
        messages.value.push({ role: 'system', content: `Error: ${event.content}` })
        isSending.value = false
    } else if (event.type === 'system') {
        messages.value.push({ role: 'system', content: event.content })
    }
}

// Watch Session ID change
watch(() => props.sessionId, async (newId) => {
    console.log('[ChatBox] sessionId changed to:', newId)
    if (!newId) {
        messages.value = []
        if (socket.value) socket.value.close()
        return
    }
    
    // Resume session via API first to ensure it's loaded in backend
    await fetch(`/api/sessions/${newId}/resume`, { method: 'POST' })
    
    messages.value = [] // TODO: Load history
    messages.value.push({ role: 'system', content: 'Session connected.' })
    
    connectWebSocket(newId)
})


onUnmounted(() => {

    if (socket.value) socket.value.close()
})

const sendMessage = async () => {
    if (!inputValue.value.trim() || isSending.value) return
    
    const text = inputValue.value
    inputValue.value = ''
    isSending.value = true
    
    // UI Update
    messages.value.push({ role: 'user', content: text })
    scrollToBottom()

    // 1. Ensure Session
    let sid = props.sessionId
    if (!sid) {
        try {
            const res = await fetch('/api/sessions', { method: 'POST' })
            const data = await res.json()
            sid = data.session_id
            emit('session-created', sid)
            
            // Wait for WS connection (triggered by watch, but we need to wait here too)
            // A simple retry loop to wait for socket.readyState === 1
            let retries = 0
            while (retries < 20) { // 2 seconds max
                if (socket.value && socket.value.readyState === WebSocket.OPEN) break    
                await new Promise(r => setTimeout(r, 100))
                retries++
            }
        } catch (e) {
            messages.value.push({ role: 'system', content: `Error creating session: ${e.message}` })
            isSending.value = false
            return
        }
    }
    
    // 2. Send Message
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
        socket.value.send(text)
    } else {
        messages.value.push({ role: 'system', content: `Error: Not connected to server.` })
        isSending.value = false
    }
}

</script>

<template>
  <div class="chat-box">
    <!-- Status Header -->
    <div class="chat-header">
       <span v-if="sessionId" class="session-id">Session: {{ sessionId.substring(0,8) }}...</span>
       <span v-else class="session-id">New Chat</span>
       
       <span v-if="isConnecting" class="status connecting">🟡 Connecting...</span>
       <span v-else-if="connectionError" class="status error">🔴 {{ connectionError }}</span>
       <span v-else-if="sessionId && socket && socket.readyState === 1" class="status connected">🟢 Connected</span>
       <span v-else class="status disconnected">⚪ Disconnected</span>
    </div>

    <div class="messages-container">
      <div v-for="(msg, index) in messages" :key="index" class="message-wrapper">
        
        <!-- Render Thoughts for Assistant Messages -->
        <div v-if="msg.thoughts && msg.thoughts.length" class="thoughts-block">
            <div v-for="(step, sIdx) in msg.thoughts" :key="sIdx" class="thought-line">
                <span v-if="step.type==='thought'">🤔 {{ step.content }}</span>
                <span v-if="step.type==='tool_call'" class="tool-call">🛠️ {{ step.name }}</span>
                <span v-if="step.type==='tool_result'" class="tool-result">✅ Result</span>
            </div>
        </div>
        
        <div :class="['message', msg.role]">
            <div v-if="msg.role === 'assistant'" v-html="md.render(msg.content)"></div>
            <div v-else>{{ msg.content }}</div>
        </div>
      </div>

      <!-- Current Streaming Block -->
      <div v-if="isSending" class="message-wrapper streaming">
         <div v-if="thoughtBuffer.length" class="thoughts-block">
            <div v-for="(step, sIdx) in thoughtBuffer" :key="sIdx" class="thought-line">
                <span v-if="step.type==='thought'">🤔 {{ step.content }}</span>
                <span v-if="step.type==='tool_call'" class="tool-call">🛠️ {{ step.name }}</span>
                <span v-if="step.type==='tool_result'" class="tool-result">✅ Result</span>
            </div>
         </div>
         <div v-if="answerBuffer" class="message assistant streaming-cursor">
             <div v-html="md.render(answerBuffer)"></div>
         </div>
         <div v-else-if="!thoughtBuffer.length" class="message assistant">...</div>
      </div>
    </div>
    
    <div class="input-area">
      <input 
        v-model="inputValue" 
        @keydown.enter="sendMessage"
        placeholder="Type a message..." 
        :disabled="isSending"
      />
      <button @click="sendMessage" :disabled="isSending">Send</button>
    </div>
  </div>
</template>

<style scoped>
.chat-box { flex: 1; display: flex; flex-direction: column; background: #0d1117; }
.chat-header {
    padding: 10px 20px;
    border-bottom: 1px solid #30363d;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #161b22;
}
.session-id { font-weight: bold; font-family: monospace; }
.status { font-size: 0.85rem; }
.status.connected { color: #238636; }
.status.connecting { color: #d29922; }
.status.error { color: #da3633; }
.status.disconnected { color: #8b949e; }

.messages-container { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.message-wrapper { display: flex; flex-direction: column; align-items: flex-start; }
.message { padding: 10px 16px; border-radius: 8px; max-width: 80%; }
.message.user { align-self: flex-end; background: #1f6feb; color: white; }
.message.assistant { background: #161b22; border: 1px solid #30363d; color: #c9d1d9; }
.message.system { align-self: center; font-size: 0.8em; color: #8b949e; }

.thoughts-block {
    margin-bottom: 8px;
    margin-left: 10px;
    padding-left: 10px;
    border-left: 2px solid #30363d;
    font-size: 0.85rem;
    color: #8b949e;
    font-family: monospace;
}
.tool-call { color: #58a6ff; }
.tool-result { color: #238636; }

.input-area { padding: 20px; border-top: 1px solid #30363d; display: flex; gap: 10px; }
input { flex: 1; padding: 10px; background: #0d1117; border: 1px solid #30363d; color: white; border-radius: 6px; }
button { padding: 10px 20px; background: #238636; color: white; border: none; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: 0.5; }
</style>
