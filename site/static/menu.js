(() => {
  const button = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("site-sidebar");

  if (!button || !sidebar) return;

  const openMenu = () => {
    document.body.classList.add("menu-open");
    button.setAttribute("aria-expanded", "true");
  };

  const closeMenu = () => {
    document.body.classList.remove("menu-open");
    button.setAttribute("aria-expanded", "false");
  };

  const toggleMenu = () => {
    if (document.body.classList.contains("menu-open")) {
      closeMenu();
    } else {
      openMenu();
    }
  };

  button.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleMenu();
  });

  sidebar.addEventListener("click", (event) => {
    const target = event.target;

    if (target instanceof HTMLAnchorElement) {
      closeMenu();
    }
  });

  document.addEventListener("click", (event) => {
    if (!document.body.classList.contains("menu-open")) return;

    const target = event.target;

    if (!(target instanceof Node)) return;
    if (sidebar.contains(target) || button.contains(target)) return;

    closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });
})();
