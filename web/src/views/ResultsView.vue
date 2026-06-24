<template>
  <main class="page results-page results-admin">
    <section class="results-header">
      <div>
        <span class="eyebrow">작업 결과</span>
        <h1 class="display-md">결과 및 관리자 요약</h1>
        <p class="muted">생산성 지표, 이벤트 로그, DB 연결 상태, 하드웨어 구성을 한 화면에서 확인합니다.</p>
      </div>
      <div class="result-actions">
        <button class="button-secondary" @click="loadData">새로고침</button>
        <button class="button-primary" @click="seedDemo">더미데이터 채우기</button>
      </div>
    </section>

    <section class="results-grid">
      <section class="product-mockup-card chart-card">
        <div class="card-title"><span>생산성 Chart.js</span><span class="eyebrow">METRICS</span></div>
        <canvas ref="chartCanvas" aria-label="Chart.js 생산성 지표"></canvas>
      </section>

      <section class="card metrics-card">
        <div class="card-title"><span>DB 지표</span><span class="eyebrow">/api/metrics</span></div>
        <div class="metric-list">
          <div v-for="(value, key) in metrics" :key="key" class="metric-row"><b>{{ value }}</b><span>{{ key }}</span></div>
        </div>
      </section>

      <section class="card hardware-card">
        <div class="card-title"><span>하드웨어 구성 요약</span><span class="eyebrow">TARGETS</span></div>
        <div class="hardware-list">
          <div class="hw"><b>Conveyor Pi</b><code>ssafy@192.168.110.142</code><span>SSH / edge control</span></div>
          <div class="hw"><b>TurtleBot4</b><code>turtlebot4@192.168.110.174</code><span>ROS_DOMAIN_ID=34</span></div>
          <div class="hw"><b>RealSense D435i</b><code>/camera/camera/color/image_raw</code><span>YOLO stream</span></div>
          <div class="hw"><b>Dobot</b><code>assembly / loading sequence</code><span>dry-run protected</span></div>
        </div>
      </section>

      <section class="card orders-card">
        <div class="card-title"><span>최근 Orders</span><span class="eyebrow">/api/orders</span></div>
        <div class="simple-list compact-list">
          <div v-for="order in orders" :key="order.id" class="simple-row">
            <strong>{{ order.command }}</strong>
            <code class="code">{{ order.destination }} · {{ order.status }}</code>
          </div>
        </div>
      </section>

      <section class="product-mockup-card events-card">
        <div class="card-title"><span>이벤트 로그</span><span class="eyebrow">/api/events</span></div>
        <div class="event-log">
          <div v-for="event in events" :key="event.id" class="event-row">
            <strong>{{ event.event_type }}</strong>
            <span>{{ event.state || 'payload' }}</span>
            <code>{{ JSON.stringify(event.payload).slice(0, 120) }}</code>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { Chart } from 'chart.js/auto';
import { nextTick, onMounted, ref } from 'vue';

const metrics = ref({ orders: 0, events: 0, vision_detections: 0, deliveries: 0, emergency_stops: 0 });
const orders = ref([]);
const events = ref([]);
const chartCanvas = ref(null);
let chart = null;

function renderChart() {
  if (!chartCanvas.value) return;
  const data = [metrics.value.orders, metrics.value.events, metrics.value.vision_detections, metrics.value.deliveries, metrics.value.emergency_stops];
  if (!chart) {
    chart = new Chart(chartCanvas.value, {
      type: 'bar',
      data: {
        labels: ['Orders', 'Events', 'Vision', 'Deliveries', 'Stops'],
        datasets: [{ label: '생산성 지표', data, backgroundColor: ['#111111', '#374151', '#6b7280', '#10b981', '#f59e0b'] }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
    return;
  }
  chart.data.datasets[0].data = data;
  chart.update('none');
}

async function loadData() {
  const [metricsRes, ordersRes, eventsRes] = await Promise.all([
    fetch('/api/metrics'),
    fetch('/api/orders'),
    fetch('/api/events'),
  ]);
  metrics.value = await metricsRes.json();
  orders.value = ((await ordersRes.json()).orders || []).slice(0, 8);
  events.value = ((await eventsRes.json()).events || []).slice(0, 12);
  await nextTick();
  renderChart();
}

async function seedDemo() {
  await fetch('/api/seed-demo', { method: 'POST' });
  await loadData();
}

onMounted(loadData);
</script>

<style>
.results-page{padding-top:24px}.results-header{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;padding:24px 0;border-bottom:1px solid var(--colors-hairline-soft)}.results-header h1{margin:4px 0 6px}.result-actions{display:flex;gap:10px;flex-wrap:wrap}.results-grid{display:grid;grid-template-columns:1.15fr .85fr;grid-template-areas:'chart metrics' 'hardware orders' 'events events';gap:18px;margin-top:24px}.chart-card{grid-area:chart;min-height:330px}.chart-card canvas{height:260px!important;width:100%}.metrics-card{grid-area:metrics}.hardware-card{grid-area:hardware}.orders-card{grid-area:orders}.events-card{grid-area:events}.metric-list{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.metric-row{background:#fff;border:1px solid var(--colors-hairline);border-radius:12px;padding:16px}.metric-row b{display:block;font-family:var(--font-display);font-size:34px;letter-spacing:-.04em}.metric-row span{color:var(--colors-muted);font-size:13px}.hardware-list{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.hw{background:#fff;border:1px solid var(--colors-hairline);border-radius:12px;padding:14px}.hw b,.hw code,.hw span{display:block}.hw code{font-family:var(--font-mono);font-size:12px;color:var(--colors-body);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hw span{margin-top:4px;color:var(--colors-muted);font-size:12px}.compact-list{max-height:310px;overflow:auto}.event-log{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-height:420px;overflow:auto}.event-row{background:var(--colors-surface-card);border-radius:12px;padding:14px}.event-row strong,.event-row span,.event-row code{display:block}.event-row span{color:var(--colors-muted);font-size:12px;margin:4px 0}.event-row code{font-family:var(--font-mono);font-size:12px;color:var(--colors-body);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}@media(max-width:1000px){.results-header{display:grid}.results-grid{grid-template-columns:1fr;grid-template-areas:'chart' 'metrics' 'hardware' 'orders' 'events'}.event-log,.hardware-list{grid-template-columns:1fr}}@media(max-width:600px){.metric-list{grid-template-columns:1fr}}
</style>
