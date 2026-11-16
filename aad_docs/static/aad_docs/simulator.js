/* Step-by-step flow simulator */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[data-component="flow"]').forEach(function (flow) {
        var steps = Array.from(flow.querySelectorAll(".plt-flow__step"));
        if (!steps.length) return;
        var current = 0;
        function update() {
            steps.forEach(function (s, idx) {
                s.classList.toggle("is-active", idx === current);
            });
        }
        var prev = flow.querySelector(".plt-flow__prev");
        var next = flow.querySelector(".plt-flow__next");
        if (prev) prev.addEventListener("click", function () { current = Math.max(0, current - 1); update(); });
        if (next) next.addEventListener("click", function () { current = Math.min(steps.length - 1, current + 1); update(); });
    });
});
