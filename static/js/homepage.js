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
