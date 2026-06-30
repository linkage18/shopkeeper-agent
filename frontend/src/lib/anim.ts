/**
 * GSAP 动画工具 — 统一管理入场/过渡/反馈动画
 * 所有动画均检查 prefers-reduced-motion
 */
import gsap from "gsap";

let _reduced = false;
if (typeof window !== "undefined") {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  _reduced = mq.matches;
  mq.addEventListener("change", () => { _reduced = mq.matches; });
}

function maybe(...args: Parameters<typeof gsap.to>) {
  if (_reduced) return;
  gsap.to(...args);
}

/** 从下方 fadeIn 上浮 */
export function fadeInUp(el: HTMLElement | null, delay = 0, duration = 0.4) {
  maybe(() => gsap.from(el, { y: 16, opacity: 0, duration, delay, ease: "power2.out" }));
}

/** 从左/右侧滑入 */
export function slideIn(el: HTMLElement | null, dir: "left" | "right" = "left", delay = 0) {
  const x = dir === "left" ? -16 : 16;
  maybe(() => gsap.from(el, { x, opacity: 0, duration: 0.35, delay, ease: "power2.out" }));
}

/** 列表项逐个 stagger 入场 */
export function staggerList(els: HTMLElement[], staggerMs = 60) {
  maybe(() => gsap.from(els, { y: 12, opacity: 0, duration: 0.3, stagger: staggerMs / 1000, ease: "power2.out" }));
}

/** 呼吸脉冲（running 态） */
export function pulse(el: HTMLElement | null) {
  if (!el || _reduced) return;
  gsap.to(el, {
    scale: 1.03, boxShadow: "0 0 12px rgba(234,179,8,0.3)",
    duration: 1.2, repeat: -1, yoyo: true, ease: "sine.inOut",
  });
}

/** 停止脉冲 */
export function killPulse(el: HTMLElement | null) {
  if (!el) return;
  gsap.killTweensOf(el);
  gsap.set(el, { scale: 1, boxShadow: "none" });
}

/** 图标弹跳确认 */
export function bounceIcon(el: HTMLElement | null) {
  maybe(() => gsap.fromTo(el, { scale: 0.8 }, { scale: 1, duration: 0.3, ease: "back.out(2)" }));
}

/** SVG 连线生长 */
export function growLine(el: HTMLElement | null, delay = 0) {
  if (!el || _reduced) return;
  const len = el.getTotalLength?.() ?? 0;
  gsap.fromTo(el, { strokeDasharray: len, strokeDashoffset: len },
    { strokeDashoffset: 0, duration: 0.5, delay, ease: "power2.inOut" });
}

/** 旋转打叉/勾 */
export function spinIcon(el: HTMLElement | null) {
  maybe(() => gsap.fromTo(el, { rotation: -180, opacity: 0 },
    { rotation: 0, opacity: 1, duration: 0.4, ease: "back.out(1.5)" }));
}

/** 字符 reveal */
export function revealText(el: HTMLElement | null, delay = 0) {
  maybe(() => gsap.from(el, { clipPath: "inset(0 100% 0 0)", duration: 0.6, delay, ease: "power2.out" }));
}

/** 高度折叠展开 */
export function expandCollapse(el: HTMLElement | null, open: boolean, duration = 0.3) {
  if (!el || _reduced) { el?.style.setProperty("display", open ? "" : "none"); return; }
  gsap.to(el, {
    height: open ? "auto" : 0, opacity: open ? 1 : 0, duration,
    ease: "power2.inOut", onStart: () => { if (open) el.style.display = ""; },
    onComplete: () => { if (!open) el.style.display = "none"; },
  });
}

/** 按钮 hover 放大 */
export function hoverScale(el: HTMLElement | null) {
  if (!el || _reduced) return;
  el.addEventListener("mouseenter", () => gsap.to(el, { scale: 1.05, duration: 0.2 }));
  el.addEventListener("mouseleave", () => gsap.to(el, { scale: 1, duration: 0.2 }));
  el.addEventListener("mousedown", () => gsap.to(el, { scale: 0.95, duration: 0.1 }));
  el.addEventListener("mouseup", () => gsap.to(el, { scale: 1.05, duration: 0.1 }));
}

/** 清除所有元素上的 GSAP 动画（组件卸载时调用） */
export function cleanup(el: HTMLElement | null) {
  if (el) gsap.killTweensOf(el);
}
