<template>
  <div class="version-info">
    <p>Current Version: {{ version }}</p>
    <a href="/CHANGELOG.html" class="vp-hero-action button">View changelog</a>
  </div>
</template>

<script>
export default {
  props: {
    version: {
      type: String,
      required: true
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

.button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 1rem 2rem;
  cursor: pointer;
  text-decoration: none;
}

.button:hover {
  background-color: #358a6b;
  text-decoration: none !important;
}
</style>