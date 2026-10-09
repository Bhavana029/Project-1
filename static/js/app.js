(function () {
  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("mainNav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  document.querySelectorAll("form.delete-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm("Delete this transaction? This cannot be undone.")) {
        e.preventDefault();
      }
    });
  });

  var typeSelect = document.getElementById("id_type");
  var categorySelect = document.getElementById("id_category");
  if (typeSelect && categorySelect && window.transactionCategories) {
    function refreshCategories() {
      var type = typeSelect.value;
      var list = window.transactionCategories[type] || [];
      var current = categorySelect.value;
      categorySelect.innerHTML = "";
      list.forEach(function (cat) {
        var opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        if (cat === current) {
          opt.selected = true;
        }
        categorySelect.appendChild(opt);
      });
      if (!list.includes(current) && list.length) {
        categorySelect.value = list[0];
      }
    }
    typeSelect.addEventListener("change", refreshCategories);
    refreshCategories();
  }

  if (window.dashboardCharts && window.Chart) {
    var primary = "#3B82F6";
    var trend = window.dashboardCharts.trend;
    if (trend.labels && trend.labels.length) {
      var trendCtx = document.getElementById("trendChart");
      if (trendCtx) {
        new Chart(trendCtx, {
          type: "line",
          data: {
            labels: trend.labels,
            datasets: [
              {
                label: "Expenses",
                data: trend.values,
                borderColor: primary,
                backgroundColor: "rgba(59, 130, 246, 0.15)",
                fill: true,
                tension: 0.25,
              },
            ],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
          },
        });
      }
    }
    var cat = window.dashboardCharts.category;
    if (cat.labels && cat.labels.length) {
      var catCtx = document.getElementById("categoryChart");
      if (catCtx) {
        new Chart(catCtx, {
          type: "doughnut",
          data: {
            labels: cat.labels,
            datasets: [
              {
                data: cat.values,
                backgroundColor: ["#3B82F6", "#60A5FA", "#93C5FD", "#2563EB", "#1D4ED8", "#64748B"],
              },
            ],
          },
          options: { responsive: true },
        });
      }
    }
  }

  if (window.reportCategory && window.Chart) {
    var labels = window.reportCategory.labels;
    var values = window.reportCategory.values;
    if (labels && labels.length) {
      var reportCtx = document.getElementById("reportCategoryChart");
      if (reportCtx) {
        new Chart(reportCtx, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [
              {
                label: "Expenses",
                data: values,
                backgroundColor: "#3B82F6",
              },
            ],
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
          },
        });
      }
    }
  }
})();
