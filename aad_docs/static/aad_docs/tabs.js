/* Progressive enhancement for Tabs component */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[data-component="tabs"]').forEach(function (tabs) {
        var buttons = Array.from(tabs.querySelectorAll(".plt-tabs__btn"));
        var panels = Array.from(tabs.querySelectorAll(".plt-tabs__panel"));
        function select(idx) {
            buttons.forEach(function (b, i) {
                b.classList.toggle("is-active", i === idx);
                b.classList.toggle("d-tab-active", i === idx);
                b.setAttribute("aria-selected", i === idx ? "true" : "false");
            });
            panels.forEach(function (p, i) { p.hidden = i !== idx; p.classList.toggle("is-active", i === idx); });
        }
        if (panels.length) select(0);
        buttons.forEach(function (btn, idx) {
            btn.addEventListener("click", function () { select(idx); });
        });
    });
});
