// Utility function to hide all popups (contact popup + future page)
function hideAllPopups() {
  const futurePage = document.getElementById("futurePage");
  const contactPopup = document.getElementById("contact-popup");

  if (futurePage) futurePage.classList.add("hidden");
  if (contactPopup) contactPopup.classList.add("hidden");
}

// Handle click on the logo to reload homepage
const logoLink = document.getElementById("logo-link");
if (logoLink) {
  logoLink.addEventListener("click", function (e) {
    hideAllPopups();
    setTimeout(function () {
      window.location.href = window.location.origin + window.location.pathname;
    }, 100);
  });
}

// Handle clicks on links that should open the future page
// Excludes contact box and proposal/position cards
const futureLinks = document.querySelectorAll(
  ".box[data-page]:not([data-page='contact']):not([data-page='about']), .nav-link:not([data-page='ongoing']):not([data-page='completed'])"
);

futureLinks.forEach((link) => {
  link.addEventListener("click", function (e) {
    e.preventDefault();
    hideAllPopups();

    const futurePage = document.getElementById("futurePage");
    if (futurePage) futurePage.classList.remove("hidden");
  });
});

// Handle back button to hide popups
const backButton = document.getElementById("backButton");
if (backButton) {
  backButton.addEventListener("click", () => {
    hideAllPopups();
  });
}

// Handle contact popup (only opens when clicking the Contact box)
const contactBox = document.querySelector('.box[data-page="contact"]');
const contactPopup = document.getElementById("contact-popup");
const closePopupBtn = document.getElementById("close-popup");

if (contactBox && contactPopup) {
  contactBox.addEventListener("click", function (e) {
    e.preventDefault();
    hideAllPopups();
    contactPopup.classList.remove("hidden");
  });
}

// Close popup when clicking the close button
if (closePopupBtn && contactPopup) {
  closePopupBtn.addEventListener("click", () => {
    contactPopup.classList.add("hidden");
  });
}

// Close contact popup when clicking outside the popup content
if (contactPopup) {
  contactPopup.addEventListener("click", (e) => {
    if (e.target === contactPopup) {
      contactPopup.classList.add("hidden");
    }
  });
}

// Dynamically update the latest 4 cards
document.addEventListener("DOMContentLoaded", async () => {
  const wrapper = document.getElementById("cards-wrapper");
  if (!wrapper) return;

  try {
    const response = await fetch("./output/latest_procedures.json");
    const procedures = await response.json();

    // Only keep the latest 4
    const latestFour = procedures.slice(0, 4);

    // Get currently displayed slugs
    const existingSlugs = Array.from(
      wrapper.querySelectorAll(".card-link")
    ).map((a) => a.dataset.page);

    // If the 4 latest slugs are identical to currently displayed, do nothing
    const latestSlugs = latestFour.map((p) => p.slug);
    const identical =
      existingSlugs.length === latestSlugs.length &&
      existingSlugs.every((slug, i) => slug === latestSlugs[i]);
    if (identical) return;

    // Otherwise, remove all existing cards
    while (wrapper.firstChild) {
      wrapper.removeChild(wrapper.firstChild);
    }

    // Add the latest 4 cards
    latestFour.forEach((proc) => {
      const mode = proc.url.includes("proposal") ? "proposal" : "position";

      const a = document.createElement("a");
      a.href = proc.url; // directly use the URL from the JSON
      a.classList.add("card-link");
      a.dataset.page = proc.slug;

      const cardDiv = document.createElement("div");
      cardDiv.classList.add("card");

      const contentDiv = document.createElement("div");
      contentDiv.classList.add("card-content");

      const stageText = mode === "proposal" ? "ONGOING" : "COMPLETED";
      const cornerDiv = document.createElement("div");
      cornerDiv.classList.add(
        stageText === "COMPLETED" ? "blue-corner-small" : "blue-corner"
      );
      const pStage = document.createElement("p");
      pStage.textContent = stageText;
      cornerDiv.appendChild(pStage);

      const dateDiv = document.createElement("div");
      dateDiv.classList.add("date");
      dateDiv.textContent = proc.date;

      const titleP = document.createElement("p");
      titleP.textContent = proc.title;

      contentDiv.appendChild(cornerDiv);
      contentDiv.appendChild(dateDiv);
      contentDiv.appendChild(titleP);
      cardDiv.appendChild(contentDiv);
      a.appendChild(cardDiv);
      wrapper.appendChild(a);
    });
  } catch (err) {
    console.error("Failed to load latest procedures JSON:", err);
  }
});
