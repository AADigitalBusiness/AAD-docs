/* Sortable and filterable table enhancement */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[data-component="table"]').forEach(function (widget) {
        var input = widget.querySelector(".plt-table-widget__filter");
        var tbody = widget.querySelector("tbody");
        if (!tbody) return;

        if (input) {
            input.addEventListener("input", function () {
                var q = input.value.toLowerCase();
                Array.from(tbody.rows).forEach(function (row) {
                    row.hidden = q && !row.textContent.toLowerCase().includes(q);
                });
            });
        }

        widget.querySelectorAll("th[data-col-index]").forEach(function (th) {
            var asc = true;
            th.addEventListener("click", function () {
                var idx = parseInt(th.getAttribute("data-col-index"), 10);
                var rows = Array.from(tbody.rows);
                rows.sort(function (a, b) {
                    var av = (a.cells[idx] ? a.cells[idx].textContent : "").trim();
                    var bv = (b.cells[idx] ? b.cells[idx].textContent : "").trim();
                    return asc ? av.localeCompare(bv) : bv.localeCompare(av);
                });
                asc = !asc;
                rows.forEach(function (r) { tbody.appendChild(r); });
            });
        });
    });
});
