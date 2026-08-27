const particles = document.querySelector(".particles");

for (let i = 0; i < 50; i++) {

    const dot = document.createElement("span");

    dot.style.left = Math.random() * 100 + "%";

    dot.style.width = dot.style.height =
        Math.random() * 6 + 3 + "px";

    dot.style.animationDuration =
        Math.random() * 12 + 8 + "s";

    dot.style.animationDelay =
        Math.random() * 5 + "s";

    particles.appendChild(dot);

}