/* CaribTech Labs - Admin dashboard behavior (vanilla JS) */

document.addEventListener("DOMContentLoaded", function () {
  initNotifDropdown();
  initModals();
  initDragReorder();
  initConfirmDelete();
});

/* ---------------------------------------------------------------------- */
/* Notification bell dropdown                                              */
/* ---------------------------------------------------------------------- */
function initNotifDropdown() {
  const bell = document.getElementById("notif-bell");
  const dropdown = document.getElementById("notif-dropdown");
  if (!bell || !dropdown) return;

  bell.addEventListener("click", function (e) {
    e.stopPropagation();
    dropdown.classList.toggle("is-open");
  });

  document.addEventListener("click", function (e) {
    if (!dropdown.contains(e.target) && e.target !== bell) {
      dropdown.classList.remove("is-open");
    }
  });

  const markAllBtn = document.getElementById("mark-all-read");
  if (markAllBtn) {
    markAllBtn.addEventListener("click", function () {
      fetch("/admin/notifications/read-all", { method: "POST" }).then(function () {
        window.location.reload();
      });
    });
  }
}

/* ---------------------------------------------------------------------- */
/* Generic modal open/close (edit forms for services, team, deals, posts)  */
/* ---------------------------------------------------------------------- */
function initModals() {
  document.querySelectorAll("[data-open-modal]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      const modalId = trigger.getAttribute("data-open-modal");
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add("is-open");
    });
  });

  document.querySelectorAll("[data-close-modal]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      const modal = trigger.closest(".modal-backdrop");
      if (modal) modal.classList.remove("is-open");
    });
  });

  document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
    backdrop.addEventListener("click", function (e) {
      if (e.target === backdrop) backdrop.classList.remove("is-open");
    });
  });
}

/* ---------------------------------------------------------------------- */
/* Drag-to-reorder for services / team lists                               */
/* ---------------------------------------------------------------------- */
function initDragReorder() {
  document.querySelectorAll("[data-reorder-list]").forEach(function (list) {
    const endpoint = list.getAttribute("data-reorder-endpoint");
    let dragged = null;

    list.querySelectorAll("[data-reorder-item]").forEach(function (item) {
      item.setAttribute("draggable", "true");

      item.addEventListener("dragstart", function () {
        dragged = item;
        item.style.opacity = "0.5";
      });

      item.addEventListener("dragend", function () {
        item.style.opacity = "1";
        const order = Array.from(list.querySelectorAll("[data-reorder-item]")).map(function (el) {
          return el.getAttribute("data-id");
        });
        fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ order: order }),
        }).catch(function () {});
      });

      item.addEventListener("dragover", function (e) {
        e.preventDefault();
        const bounding = item.getBoundingClientRect();
        const offset = e.clientY - bounding.top;
        if (dragged && dragged !== item) {
          if (offset > bounding.height / 2) {
            item.after(dragged);
          } else {
            item.before(dragged);
          }
        }
      });
    });
  });
}

/* ---------------------------------------------------------------------- */
/* Confirm before destructive actions                                      */
/* ---------------------------------------------------------------------- */
function initConfirmDelete() {
  document.querySelectorAll("[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const message = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });
}
