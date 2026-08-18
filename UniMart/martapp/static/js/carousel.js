window.addEventListener("load", function () {

    const slider = document.getElementById("heroSlider");
    const slides = document.querySelectorAll(".hero-slide");
    const nextBtn = document.getElementById("nextBtn");
    const prevBtn = document.getElementById("prevBtn");
    const dots = document.querySelectorAll(".dot");

    if (!slider || slides.length === 0) {
        return;
    }
    let current = 0;
    function showSlide(index) {
        current = index;
        slider.style.transform =
            `translateX(-${current * 100}%)`;
        dots.forEach(function (dot, i) {
            if (i === current) {
                dot.classList.remove("bg-white/50");
                dot.classList.add("bg-white");
            } else {
                dot.classList.remove("bg-white");
                dot.classList.add("bg-white/50");
            }

        });
    }
    nextBtn.addEventListener("click", function () {
        current++;
        if (current >= slides.length) {
            current = 0;
        }
        showSlide(current);
    });

    prevBtn.addEventListener("click", function () {
        current--;
        if (current < 0) {
            current = slides.length - 1;
        }
        showSlide(current);
    });
    dots.forEach(function (dot, index) {
        dot.addEventListener("click", function () {
            showSlide(index);
        });

    });
    showSlide(0);
    setInterval(function () {

        current++;

        if (current >= slides.length) {
            current = 0;
        }

        showSlide(current);

    }, 3000);

});