/* Build local document navigation using text nodes, never injected HTML. */
(() => {
    const list = document.getElementById("aad-docs-outline");
    const empty = document.getElementById("aad-docs-outline-empty");
    const article = document.querySelector(".plt-docs__main > article");
    if (!list || !empty || !article) return;
    const headings = article.querySelectorAll("h2, h3");
    const used = new Set(Array.from(document.querySelectorAll("[id]"), el => el.id));
    headings.forEach((heading, index) => {
        if (!heading.id) {
            let id = "aad-docs-section-" + (index + 1);
            while (used.has(id)) id += "-section";
            heading.id = id;
            used.add(id);
        }
        const item = document.createElement("li");
        item.dataset.level = heading.tagName.slice(1);
        const link = document.createElement("a");
        link.href = "#" + encodeURIComponent(heading.id);
        link.textContent = heading.textContent;
        item.append(link);
        list.append(item);
    });
    empty.hidden = headings.length > 0;
})();
