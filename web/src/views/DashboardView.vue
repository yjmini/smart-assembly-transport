<template>
  <main class="page home-page dashboard-page">
    <section class="home-hero section-shell">
      <div class="hero-copy">
        <span class="badge-pill">Smart factory operation dashboard</span>
        <h1 class="display-xl">Smart Assembly Transport Control Center</h1>
        <p class="hero-subtitle">컨베이어, Dobot, RealSense, TurtleBot, STT/TTS 공정을 작업 진행 화면과 작업 결과 화면으로 분리한 운영 대시보드입니다.</p>
        <div class="hero-actions">
          <router-link to="/progress" class="button-primary">공정 시작하기</router-link>
          <router-link to="/results" class="button-secondary">작업 결과 확인</router-link>
        </div>
      </div>
      <aside class="product-mockup-card summary-card">
        <div class="card-title"><span>현재 상태 요약</span><span class="eyebrow">READY</span></div>
        <div class="summary-grid">
          <div><b>DRY-RUN</b><span>기본 실행 모드</span></div>
          <div><b>2</b><span>배송 목적지</span></div>
          <div><b>11</b><span>공정 단계</span></div>
          <div><b>5</b><span>연동 모듈</span></div>
        </div>
        <div class="system-list">
          <span>WebSocket mission server</span>
          <span>Vue Router dashboard</span>
          <span>Django API / DB metrics</span>
        </div>
      </aside>
    </section>

    <section class="section-shell guide-section">
      <div class="section-heading">
        <span class="eyebrow">사용 방법</span>
        <h2 class="display-lg">작업 흐름</h2>
      </div>
      <div class="guide-grid">
        <div class="card guide-card">
          <span class="step-index">01</span>
          <h3>작업 진행</h3>
          <p>WebSocket 연결 후 STT/Mock 작업을 시작하고, 비전·지도·음성 상태와 작업 타임라인을 확인합니다.</p>
        </div>
        <div class="card guide-card">
          <span class="step-index">02</span>
          <h3>상태 대응</h3>
          <p>작업 중 손 감지/비상정지, 관리자 Unlock, 실제 실행 모드 전환을 작업 진행 화면에서 처리합니다.</p>
        </div>
        <div class="card guide-card">
          <span class="step-index">03</span>
          <h3>작업 결과</h3>
          <p>생산성 지표, 이벤트 로그, DB 더미데이터, 하드웨어 구성 요약을 작업 결과 화면에서 확인합니다.</p>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
</script>

<style>
.home-page{padding-top:0}.home-hero{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:48px;align-items:center;min-height:520px}.hero-copy{max-width:680px}.hero-copy h1{margin:20px 0 18px}.hero-subtitle{color:var(--colors-body);font-size:18px;max-width:640px;margin:0 0 28px}.hero-actions{display:flex;gap:12px;flex-wrap:wrap}.summary-card{display:grid;gap:20px}.card-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px;font-weight:700;color:var(--colors-ink)}.summary-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.summary-grid div{background:var(--colors-surface-card);border-radius:12px;padding:18px}.summary-grid b{display:block;font-family:var(--font-display);font-size:36px;line-height:1;letter-spacing:-.04em}.summary-grid span,.system-list span{display:block;color:var(--colors-muted);font-size:14px;margin-top:6px}.system-list{display:grid;gap:8px;padding-top:16px;border-top:1px solid var(--colors-hairline)}.guide-section{padding-top:72px}.section-heading{max-width:760px;margin-bottom:28px}.section-heading h2{margin:8px 0}.guide-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.guide-card h3{margin:16px 0 8px;font-size:20px}.guide-card p{margin:0;color:var(--colors-body)}.step-index{font-family:var(--font-mono);color:var(--colors-muted);font-size:13px;font-weight:700}@media(max-width:900px){.home-hero,.guide-grid{grid-template-columns:1fr}.home-hero{min-height:auto}.summary-grid{grid-template-columns:1fr 1fr}}@media(max-width:560px){.summary-grid{grid-template-columns:1fr}}
</style>
