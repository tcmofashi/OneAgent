<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps(['currentSessionId'])
const emit = defineEmits(['select-session'])
const sessions = ref([])

const loadSessions = async () => {
  try {
    const res = await fetch('/api/sessions')
    sessions.value = await res.json()
  } catch (e) {
    console.error(e)
  }
}

const selectSession = (id) => {
  emit('select-session', id)
}

const createNewChat = async () => {
  try {
    const res = await fetch('/api/sessions', { method: 'POST' })
    const data = await res.json()
    // Refresh list
    await loadSessions()
    // Select new session
    emit('select-session', data.session_id)
  } catch (e) {
    console.error("Failed to create session", e)
  }
}

onMounted(loadSessions)
</script>

<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>OneAgent</h2>
      <button @click="createNewChat" class="new-chat-btn">+ New Chat</button>
    </div>
    <div class="session-list">
      <div 
        v-for="session in sessions" 
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === currentSessionId }"
        @click="selectSession(session.id)"
      >
        Session {{ session.id.substring(0, 8) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  width: 260px;
  background-color: #0d1117;
  border-right: 1px solid #30363d;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #30363d;
}
.new-chat-btn {
  width: 100%;
  padding: 8px;
  background: #238636;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.session-list {
  flex: 1;
  overflow-y: auto;
}
.session-item {
  padding: 10px 16px;
  cursor: pointer;
  color: #c9d1d9;
  border-bottom: 1px solid #21262d;
}
.session-item:hover {
  background: #161b22;
}
.session-item.active {
  background: #1f2937;
  border-left: 4px solid #58a6ff;
}
</style>
