import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getProfile, updateProfile, updateUsername, uploadAvatar } from '../api/user'

export const useUserStore = defineStore('user', () => {
  const id = ref(null)
  const username = ref('')
  const displayName = ref('')
  const avatarUrl = ref('')

  async function fetchProfile() {
    const res = await getProfile()
    const data = res.data
    id.value = data.id
    username.value = data.username
    displayName.value = data.display_name || data.username
    avatarUrl.value = data.avatar_url || ''
  }

  async function updateDisplayName(name) {
    await updateProfile({ display_name: name })
    displayName.value = name
  }

  async function changeUsername(newUsername) {
    await updateUsername(newUsername)
    username.value = newUsername
  }

  async function changeAvatar(file) {
    const res = await uploadAvatar(file)
    avatarUrl.value = res.data.avatar_url
  }

  return { id, username, displayName, avatarUrl, fetchProfile, updateDisplayName, changeUsername, changeAvatar }
})
