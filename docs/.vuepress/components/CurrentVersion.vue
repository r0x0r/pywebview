<template>
  <div class="version-info">
    <p>Current Version: {{ version }}</p>
    <button @click="goToChangelog" class="vp-hero-action">View Changelog</button>
  </div>
</template>

<script>
export default {
  props: {
    version: {
      type: String,
      required: true
    }
  },
  methods: {
    goToChangelog() {
      window.location.href = '/CHANGELOG';
    }
  }
}
</script>

<style scoped>
.version-info {
  text-align: center;
  font-size: 18px;
  margin: 2rem 0 4rem 0;
  color: #6a8bad;
}

button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 1rem 2rem;
  cursor: pointer;
}

button:hover {
  background-color: #358a6b;
}
</style>