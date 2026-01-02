<script setup>
import ChatBox from './components/ChatBox.vue'
import Sidebar from './components/Sidebar.vue'
import { ref } from 'vue'

const currentSessionId = ref(null)

const handleSessionSelect = (sessionId) => {
    currentSessionId.value = sessionId
}
</script>

<template>
  <div class="app-container">
    <Sidebar @select-session="handleSessionSelect" :current-session-id="currentSessionId" />
    <ChatBox :session-id="currentSessionId" @session-created="(id) => currentSessionId = id" />
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
</style>
