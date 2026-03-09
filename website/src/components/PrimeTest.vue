<template>
  <div class="card flex flex-col items-center gap-4 p-6 border rounded-xl bg-white shadow-lg max-w-md mx-auto my-8">
    <h3 class="text-2xl font-bold text-gray-800">PrimeVue Aura Test</h3>
    <div class="flex flex-col gap-2 w-full">
      <label for="username" class="font-semibold">Username</label>
      <InputText id="username" v-model="text" placeholder="Enter username" fluid />
    </div>
    <Button label="Submit" @click="greet" class="w-full" />
    <p v-if="text" class="text-green-600 font-medium">Reactivity check: {{ text }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';

const text = ref('');

onMounted(() => {
  console.log('PrimeTest component mounted');
});

const greet = () => {
  alert('PrimeVue is working! You typed: ' + text.value);
};
</script>

<style scoped>
/* You can use Tailwind classes directly in PrimeVue components if they're configured properly */
</style>

