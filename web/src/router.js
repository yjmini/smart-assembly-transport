import { createRouter, createWebHashHistory } from 'vue-router';
import DashboardView from './views/DashboardView.vue';
import ProgressView from './views/ProgressView.vue';
import ResultsView from './views/ResultsView.vue';

export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: DashboardView },
    { path: '/progress', name: 'progress', component: ProgressView },
    { path: '/results', name: 'results', component: ResultsView },
  ],
});
