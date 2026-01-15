document.addEventListener("DOMContentLoaded", function () {
  // 1. DOM Selectors
  const overlay = document.getElementById("filter-overlay");
  const popup = document.getElementById("all-filters-popup");
  const closeBtn = document.getElementById("close-popup-btn");
  const container = document.getElementById("procedures-container");
  const cards = Array.from(document.querySelectorAll(".procedure-card"));

  // Required containers for dynamically generated filter options
  const yearOptionsContainer = document.getElementById("year-options");
  const subjectOptionsContainer = document.getElementById("subject-options");

  // Mapping of subject codes to human-readable labels
  const SUBJECT_LABELS = {
    1: "European citizenship",
    2: "Internal market, single market",
    3: "Community policies",
    4: "Economic, social and territorial cohesion",
    5: "Economic and monetary system",
    6: "External relations of the Union",
    7: "Area of freedom, security and justice",
    8: "State and evolution of the Union",
    9: "Other topics",
  };

  // 2. Filter buttons  (pill)
  function createPill(value, labelText, name, type = "checkbox") {
    const label = document.createElement("label");
    label.className = "pill-btn";

    const input = document.createElement("input");
    input.type = type;
    input.name = name;
    input.value = value;

    // Default sort order is descending
    if (type === "radio" && value === "desc") input.checked = true;

    const span = document.createElement("span");
    span.textContent = labelText;

    label.appendChild(input);
    label.appendChild(span);

    // Re-filter content whenever a pill state changes
    input.addEventListener("change", updateDisplay);
    return label;
  }

  // 3. Dynamic filter option generation

  // Year filter options (sorted descending)
  const yearSet = new Set(cards.map((c) => c.dataset.year).filter(Boolean));
  Array.from(yearSet)
    .sort((a, b) => b - a)
    .forEach((year) => {
      yearOptionsContainer.appendChild(createPill(year, year, "years"));
    });

  // Subject filter options (collected from card datasets)
  const subjectSet = new Set();
  cards.forEach((card) => {
    if (card.dataset.subjects) {
      card.dataset.subjects.split("|").forEach((code) => {
        if (code.trim()) subjectSet.add(code.trim());
      });
    }
  });

  Array.from(subjectSet)
    .sort((a, b) => a - b)
    .forEach((code) => {
      const labelText = SUBJECT_LABELS[code] || `Subject ${code}`;
      subjectOptionsContainer.appendChild(
        createPill(code, labelText, "subjects")
      );
    });

  // 4. Filtering and sorting logic
  function updateDisplay() {
    // Collect selected filter values
    const selectedStatuses = Array.from(
      document.querySelectorAll('input[name="status"]:checked')
    ).map((i) => i.value);

    const selectedYears = Array.from(
      document.querySelectorAll('input[name="years"]:checked')
    ).map((i) => i.value);

    const selectedSubjects = Array.from(
      document.querySelectorAll('input[name="subjects"]:checked')
    ).map((i) => i.value);

    const sortOrder =
      document.querySelector('input[name="order"]:checked')?.value || "desc";

    // Apply filters to each card
    cards.forEach((card) => {
      const matchesStatus =
        selectedStatuses.length === 0 ||
        selectedStatuses.includes(card.dataset.status);

      const matchesYear =
        selectedYears.length === 0 || selectedYears.includes(card.dataset.year);

      const cardSubjects = card.dataset.subjects
        ? card.dataset.subjects.split("|")
        : [];

      const matchesSubject =
        selectedSubjects.length === 0 ||
        selectedSubjects.some((s) => cardSubjects.includes(s));

      card.style.display =
        matchesStatus && matchesYear && matchesSubject ? "block" : "none";
    });

    // Sort visible cards by raw date value
    const visibleCards = cards.filter((c) => c.style.display !== "none");
    visibleCards.sort((a, b) => {
      const dateA = a.dataset.dateRaw || "";
      const dateB = b.dataset.dateRaw || "";
      return sortOrder === "desc"
        ? dateB.localeCompare(dateA)
        : dateA.localeCompare(dateB);
    });

    // Re-append cards in sorted order
    visibleCards.forEach((c) => container.appendChild(c));
  }

  // 5. Popup and UI event handlers
  const closePopup = () => {
    overlay.classList.remove("active");
    popup.classList.remove("active");
    document.body.classList.remove("modal-open");
  };

  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      overlay.classList.add("active");
      popup.classList.add("active");
      document.body.classList.add("modal-open");
    });
  });

  // Update display immediately when sort order changes
  document.querySelectorAll('input[name="order"]').forEach((radio) => {
    radio.addEventListener("change", updateDisplay);
  });

  if (closeBtn) closeBtn.addEventListener("click", closePopup);
  overlay.addEventListener("click", closePopup);

  const applyBtn = document.getElementById("apply-filters");
  if (applyBtn) {
    applyBtn.addEventListener("click", () => {
      closePopup();
      updateDisplay();
    });
  }

  const resetBtn =
    document.getElementById("reset-filters-popup") ||
    document.getElementById("reset-filters");

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      document
        .querySelectorAll('.filter-popup input[type="checkbox"]')
        .forEach((i) => (i.checked = false));

      document
        .querySelectorAll('input[name="order"]')
        .forEach((i) => (i.checked = i.value === "desc"));

      updateDisplay();
    });
  }

  // Initial render
  updateDisplay();
});
