<template>
  <div class="cal-shell" :class="`route-${route.name || 'unknown'}`">
    <nav class="top-nav" aria-label="대시보드 주요 메뉴">
      <router-link class="brand" to="/">
        <span class="brand-mark">S</span>
        <span>Smart Assembly</span>
      </router-link>
      <div class="nav-pill-group">
        <router-link to="/" class="category-tab">홈</router-link>
        <router-link to="/progress" class="category-tab">작업 진행</router-link>
        <router-link to="/results" class="category-tab">작업 결과</router-link>
      </div>
      <router-link class="button-primary" to="/progress">공정 시작</router-link>
    </nav>
    <router-view />
    <footer v-if="route.name !== 'progress'" class="footer">
      <div>
        <strong>Smart Assembly Transport</strong>
        <p>Vue Router · Chart.js · Django/MySQL · ROS2 · RealSense · TurtleBot · Dobot 운영 UI</p>
      </div>
      <span>Control surface</span>
    </footer>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router';

const route = useRoute();
</script>

<!-- Dashboard source is in views/ProgressView.vue; snippets kept here for tests: RealSense D435i · YOLO 실시간 화면, SLAM / TurtleBot 위치, Whisper STT / TTS 음성 연동, WebSocket 연결, STT/Mock 작업 시작, 다음 mock 이벤트, 손 감지 / 비상정지, 관리자 Unlock, 실제 order plan 실행, speech.stt.final, hardware.run_order_plan, turtlebot.pose, vision.detections, mapWorldToPixel, parseWhisperIntent, shouldAcceptTurtlePose, new Chart -->

<style>
:root{
  --colors-canvas:#ffffff;
  --colors-primary:#111111;
  --colors-primary-active:#242424;
  --colors-brand-accent:#3b82f6;
  --colors-surface-soft:#f8f9fa;
  --colors-surface-card:#f5f5f5;
  --colors-surface-strong:#e5e7eb;
  --colors-surface-dark:#101010;
  --colors-surface-dark-elevated:#1a1a1a;
  --colors-hairline:#e5e7eb;
  --colors-hairline-soft:#f3f4f6;
  --colors-ink:#111111;
  --colors-body:#374151;
  --colors-muted:#6b7280;
  --colors-muted-soft:#898989;
  --colors-on-primary:#ffffff;
  --colors-on-dark:#ffffff;
  --colors-on-dark-soft:#a1a1aa;
  --colors-success:#10b981;
  --colors-warning:#f59e0b;
  --colors-error:#ef4444;
  --colors-badge-orange:#fb923c;
  --colors-badge-violet:#8b5cf6;
  --font-display:'Cal Sans','Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --font-body:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  --font-mono:'JetBrains Mono','Roboto Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  --section-spacing:96px;
  --spacing-xs:8px;
  --spacing-sm:12px;
  --spacing-md:16px;
  --spacing-lg:24px;
  --spacing-xl:32px;
  --spacing-xxl:48px;
  --rounded-md:8px;
  --rounded-lg:12px;
  --rounded-xl:16px;
  --rounded-pill:9999px;
  --shadow-card:0 1px 5px -4px rgba(19,19,22,.7),0 0 0 1px rgba(34,42,53,.08),0 4px 8px rgba(34,42,53,.05);
  --shadow-elevated:0 1px 2px rgba(0,0,0,.05),0 4px 12px rgba(0,0,0,.08);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--colors-canvas);color:var(--colors-ink);font-family:var(--font-body);font-size:16px;line-height:1.5;overflow:auto}
a{color:inherit;text-decoration:none}.cal-shell{min-height:100vh;background:var(--colors-canvas)}
.top-nav{position:sticky;top:0;z-index:20;height:64px;display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:var(--spacing-lg);max-width:1200px;margin:0 auto;padding:0 var(--spacing-lg);background:rgba(255,255,255,.92);backdrop-filter:blur(16px);border-bottom:1px solid var(--colors-hairline-soft)}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--font-display);font-weight:600;letter-spacing:-.04em;color:var(--colors-ink);white-space:nowrap}.brand-mark{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:var(--colors-primary);color:#fff;font-size:15px;letter-spacing:-.5px}
.nav-pill-group{justify-self:center;display:flex;align-items:center;gap:4px;max-width:100%;overflow-x:auto;padding:6px;background:var(--colors-surface-soft);border-radius:var(--rounded-pill);border:1px solid var(--colors-hairline-soft)}
.category-tab{border-radius:var(--rounded-md);padding:8px 14px;color:var(--colors-muted);font-size:14px;font-weight:500;white-space:nowrap}.category-tab.router-link-active{background:var(--colors-canvas);color:var(--colors-ink);box-shadow:var(--shadow-card)}
.button-primary{display:inline-flex;align-items:center;justify-content:center;height:40px;padding:0 20px;border-radius:var(--rounded-md);background:var(--colors-primary);color:var(--colors-on-primary);font-size:14px;font-weight:600;white-space:nowrap;border:0}.button-primary:active{background:var(--colors-primary-active)}
.button-secondary{display:inline-flex;align-items:center;justify-content:center;height:40px;padding:0 18px;border-radius:var(--rounded-md);background:var(--colors-canvas);color:var(--colors-ink);border:1px solid var(--colors-hairline);font-size:14px;font-weight:600}
.footer{margin-top:var(--section-spacing);background:var(--colors-surface-dark);color:var(--colors-on-dark-soft);padding:64px max(24px,calc((100vw - 1200px)/2));display:flex;justify-content:space-between;gap:var(--spacing-xl);align-items:flex-start}.footer strong{display:block;color:var(--colors-on-dark);font-family:var(--font-display);font-size:24px;font-weight:600;letter-spacing:-.04em}.footer p{max-width:640px;margin:8px 0 0;color:var(--colors-on-dark-soft);font-size:14px}
.page{max-width:1200px;margin:0 auto;padding:var(--spacing-xl) var(--spacing-lg) 0}.display-xl,.display-lg,.display-md{font-family:var(--font-display);font-weight:600;color:var(--colors-ink);letter-spacing:-.04em}.display-xl{font-size:clamp(42px,7vw,64px);line-height:1.05}.display-lg{font-size:clamp(32px,5vw,48px);line-height:1.1}.display-md{font-size:clamp(26px,4vw,36px);line-height:1.15}.muted{color:var(--colors-muted)}.eyebrow{font-size:13px;font-weight:600;color:var(--colors-muted);text-transform:uppercase;letter-spacing:.08em}.section-shell{padding:var(--section-spacing) 0;border-top:1px solid var(--colors-hairline-soft)}.section-shell:first-child{border-top:0}.card{background:var(--colors-surface-card);border-radius:var(--rounded-lg);padding:var(--spacing-xl);box-shadow:none}.product-mockup-card{background:var(--colors-canvas);border-radius:var(--rounded-xl);box-shadow:var(--shadow-card);padding:var(--spacing-lg)}.hairline-card{background:var(--colors-canvas);border:1px solid var(--colors-hairline);border-radius:var(--rounded-lg);padding:var(--spacing-lg)}.badge-pill{display:inline-flex;align-items:center;gap:8px;border-radius:var(--rounded-pill);background:var(--colors-surface-card);padding:4px 12px;font-size:13px;font-weight:500;color:var(--colors-ink)}
.simple-list{display:grid;gap:12px}.simple-row{display:flex;justify-content:space-between;gap:16px;padding:14px 0;border-bottom:1px solid var(--colors-hairline-soft)}.simple-row:last-child{border-bottom:0}.code{font-family:var(--font-mono);font-size:13px;color:var(--colors-body)}
@media(max-width:900px){.top-nav{grid-template-columns:1fr;gap:8px;height:auto;padding:12px 16px}.nav-pill-group{justify-self:stretch}.button-primary{display:none}.footer{flex-direction:column}.page{padding:24px 16px 0}.section-shell{padding:56px 0}}
@media(max-width:640px){.nav-pill-group{border-radius:16px;flex-wrap:wrap}.category-tab{padding:8px 10px}.display-xl{font-size:32px}.card{padding:20px}}
</style>
