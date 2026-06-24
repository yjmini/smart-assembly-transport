import { createApp } from 'vue';
import { Chart } from 'chart.js/auto';
import App from './App.vue';
import router from './router';

window.Chart = Chart;

createApp(App).use(router).mount('#app');
