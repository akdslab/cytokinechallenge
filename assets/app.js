"use strict";
document.documentElement.classList.add("js");

const menuButton = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#primary-nav");
if (menuButton && navigation) {
  const closeMenu = () => {
    menuButton.setAttribute("aria-expanded", "false");
    navigation.classList.remove("is-open");
  };
  menuButton.addEventListener("click", () => {
    const open = menuButton.getAttribute("aria-expanded") !== "true";
    menuButton.setAttribute("aria-expanded", String(open));
    navigation.classList.toggle("is-open", open);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
      closeMenu();
      menuButton.focus();
    }
  });
  navigation.addEventListener("click", event => { if (event.target.closest("a")) closeMenu(); });
}

document.querySelectorAll("[data-copy]").forEach(button => {
  const originalLabel = button.textContent;
  button.addEventListener("click", async () => {
    const target = document.getElementById(button.dataset.copy);
    const status = document.getElementById("copy-status");
    if (!target) return;
    try {
      await navigator.clipboard.writeText(target.textContent);
      button.textContent = "Copied";
      if (status) status.textContent = "Text copied to clipboard.";
      window.setTimeout(() => { button.textContent = originalLabel; }, 1800);
    } catch (_) {
      const range = document.createRange();
      range.selectNodeContents(target);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = "Select & copy";
      if (status) status.textContent = "Code selected. Use your device’s copy command.";
    }
  });
});

const glossarySearch = document.querySelector("[data-glossary-search]");
if (glossarySearch) {
  const entries = [...document.querySelectorAll(".glossary-item")];
  const status = document.getElementById("glossary-status");
  glossarySearch.disabled = false;
  const filterTerms = () => {
    const query = glossarySearch.value.trim().toLocaleLowerCase();
    let count = 0;
    entries.forEach(entry => {
      const matches = entry.textContent.toLocaleLowerCase().includes(query);
      entry.hidden = !matches;
      if (matches) count += 1;
    });
    status.textContent = count ? `${count} of ${entries.length} terms` : "No matching terms. Try another word.";
  };
  glossarySearch.addEventListener("input", filterTerms);
  window.addEventListener("hashchange", () => {
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) { return; }
    if (target && entries.includes(target)) {
      glossarySearch.value = "";
      filterTerms();
      target.scrollIntoView();
    }
  });
  filterTerms();
}

const feedbackForm = document.getElementById("feedback-form");
if (feedbackForm) {
  const topic = document.getElementById("feedback-topic");
  const summary = document.getElementById("feedback-summary");
  const details = document.getElementById("feedback-details");
  const output = document.getElementById("feedback-draft");
  const renderDraft = () => {
    const topicLabel = topic.selectedOptions[0].textContent;
    output.textContent = `Topic: ${topicLabel}\n\nSummary: ${summary.value.trim() || "[Add a summary]"}\n\nDetails:\n${details.value.trim() || "[Add details]"}`;
  };
  feedbackForm.addEventListener("submit", event => event.preventDefault());
  feedbackForm.addEventListener("input", renderDraft);
  feedbackForm.addEventListener("change", renderDraft);
  feedbackForm.addEventListener("reset", () => window.setTimeout(renderDraft, 0));
  renderDraft();
}

const splitData = {
  combination: {
    train: ["Control", "A", "B", "C", "A + C"], test: ["A + B"],
    trainNote: "Individual cytokines and a subset of measured combinations.",
    testNote: "Exclude this combination from fitting and tuning across all donors.",
    title: "New combinations of familiar cytokines",
    description: "Keep each constituent cytokine and the evaluation donors represented in training. Hold out complete combinations to measure prediction beyond the observed conditions.",
    status: "Recommended starting task"
  },
  order: {
    train: ["Control", "A", "B", "C", "A + B", "A + C", "B + C"], test: ["A + B + C"],
    trainNote: "Controls, individual cytokines, and measured pairs.",
    testNote: "Keep triple responses out of fitting and tuning.",
    title: "Transfer from smaller to larger combinations",
    description: "Predict measured triples using only single-cytokine and pair conditions. Keep donors represented in training and report which component conditions were measured.",
    status: "Requires measured larger combinations"
  },
  context: {
    train: ["Donor 1 · A + B", "Donor 2 · A + B"], test: ["Donor 3 · A + B"],
    trainNote: "The same cytokine conditions in other donors.",
    testNote: "Perturbation responses from this donor are reserved for evaluation.",
    title: "Generalization to held-out donors",
    description: "Exclude the evaluation donor from model fitting and tuning. Evaluate conditions represented in training donors, and report whether the new donor’s control profiles are supplied at prediction time.",
    status: "Requires overlapping conditions across donors"
  }
};
const splitRoot = document.querySelector("[data-split-explorer]");
if (splitRoot) {
  const tabs = [...splitRoot.querySelectorAll("[data-split]")];
  const panel = splitRoot.querySelector("#split-panel");
  const setText = (id, text) => { document.getElementById(id).textContent = text; };
  const setChips = (id, labels) => {
    document.getElementById(id).replaceChildren(...labels.map(label => {
      const item = document.createElement("span"); item.textContent = label; return item;
    }));
  };
  const select = tab => {
    const data = splitData[tab.dataset.split];
    tabs.forEach(item => { item.setAttribute("aria-selected", String(item === tab)); item.tabIndex = item === tab ? 0 : -1; });
    panel.setAttribute("aria-labelledby", tab.id);
    setChips("split-train", data.train); setChips("split-test", data.test);
    setText("split-train-note", data.trainNote); setText("split-test-note", data.testNote);
    setText("split-title", data.title); setText("split-description", data.description); setText("split-status", data.status);
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); select(tabs[next]); tabs[next].focus(); }
    });
  });
}
