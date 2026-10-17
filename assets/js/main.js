// Progressive enhancements for the case study page. Everything works without this file.

// Opens the wireflow in a modal dialog. Without <dialog> support (or without JS),
// the trigger is a plain link to the full-size image.
function initLightbox() {
  const trigger = document.querySelector(".wireflow-open");
  const dialog = document.getElementById("wireflow-dialog");
  if (!trigger || !dialog || typeof dialog.showModal !== "function") return;

  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    dialog.showModal();
  });

  dialog.querySelector(".lightbox-close").addEventListener("click", () => dialog.close());

  // A click on the backdrop lands on the <dialog> element itself.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  // Esc is handled natively; every close path returns focus to the trigger.
  dialog.addEventListener("close", () => trigger.focus());
}

// Opens a walkthrough screen at full size, with previous/next and arrow keys.
// Without JS (or <dialog>), each screen is a plain link to its full-size image.
function initScreenViewer() {
  const dialog = document.getElementById("screen-dialog");
  const triggers = [...document.querySelectorAll(".step-open")];
  if (!dialog || !triggers.length || typeof dialog.showModal !== "function") return;

  const img = dialog.querySelector(".screen-viewer-img");
  const time = dialog.querySelector(".screen-viewer-time");
  const text = dialog.querySelector(".screen-viewer-text");
  const count = dialog.querySelector(".screen-viewer-count");
  const prev = dialog.querySelector(".screen-prev");
  const next = dialog.querySelector(".screen-next");
  let index = 0;

  const show = (i) => {
    index = Math.min(Math.max(i, 0), triggers.length - 1);
    const link = triggers[index];
    const step = link.closest(".step");
    img.src = link.getAttribute("href");
    img.alt = link.querySelector("img").alt;
    time.textContent = step.querySelector(".step-time").textContent;
    text.textContent = step.querySelector(".step-text p:not(.step-time):not(.need)").textContent;
    count.textContent = `${index + 1} / ${triggers.length}`;
    prev.disabled = index === 0;
    next.disabled = index === triggers.length - 1;
    // A button that just disabled itself would drop keyboard focus; hand it over.
    if (document.activeElement === prev && prev.disabled) next.focus();
    if (document.activeElement === next && next.disabled) prev.focus();
  };

  triggers.forEach((link, i) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      show(i);
      dialog.showModal();
    });
  });

  // The browser would return focus to whichever screen opened the viewer; the reader
  // may have paged on since, so every way of closing returns it to the screen last viewed.
  // Deferred a tick so it lands after the browser's own focus restoration.
  const restoreFocus = () => setTimeout(() => triggers[index].focus(), 0);
  const closeViewer = () => {
    dialog.close();
    restoreFocus();
  };

  prev.addEventListener("click", () => show(index - 1));
  next.addEventListener("click", () => show(index + 1));
  dialog.querySelector(".lightbox-close").addEventListener("click", closeViewer);

  // A click on the backdrop lands on the <dialog> element itself.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeViewer();
  });

  dialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight") show(index + 1);
    if (event.key === "ArrowLeft") show(index - 1);
  });

  dialog.addEventListener("cancel", restoreFocus); // Esc
  dialog.addEventListener("close", restoreFocus);
}

// Fades sections in as they scroll into view. CSS only hides .reveal under the
// `js` class, so if this script never runs, everything stays visible.
function initReveal() {
  if (!("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("js");

  const sections = document.querySelectorAll(".reveal");
  const revealAll = () => sections.forEach((el) => el.classList.add("is-visible"));
  let observerFired = false;

  const observer = new IntersectionObserver((entries) => {
    observerFired = true;
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    }
  // Any overlap counts (threshold 0): a ratio threshold would never fire for
  // sections taller than a few screens, leaving them invisible on phones.
  }, { threshold: 0, rootMargin: "0px 0px -12% 0px" });

  sections.forEach((el) => observer.observe(el));

  // An observer always reports once right after observe(). If it never does
  // (some webviews and preview tools), show everything rather than a blank page.
  setTimeout(() => { if (!observerFired) revealAll(); }, 1500);

  // Printing / Save as PDF never scrolls, so unrevealed sections would print blank.
  window.addEventListener("beforeprint", revealAll);
}

// Marks the menu link for the section currently under the sticky bar.
// A section counts as current once its top passes ~30% down the viewport; sections
// without a menu link (like the closing one) clear the highlight.
function initActiveSection() {
  const links = [...document.querySelectorAll(".topbar-links a")];
  const sections = [...document.querySelectorAll("main > section")];
  if (!links.length || !sections.length) return;

  const linkFor = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));

  const update = () => {
    const line = window.innerHeight * 0.3;
    let current = null;
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= line) current = section.id;
    }
    for (const [id, link] of linkFor) {
      if (id === current) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }
  };

  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  update();
}

initReveal();

document.addEventListener("DOMContentLoaded", () => {
  initLightbox();
  initScreenViewer();
  initActiveSection();
});
