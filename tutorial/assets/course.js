(function () {
  "use strict";

  function loadStylesheet(href) {
    if (document.querySelector('link[href="' + href + '"]')) return;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function initPrismAndMermaid() {
    loadStylesheet(
      "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css"
    );
    loadScript("https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js")
      .then(function () {
        return loadScript(
          "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-c.min.js"
        );
      })
      .then(function () {
        return loadScript(
          "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-cpp.min.js"
        );
      })
      .then(function () {
        return loadScript(
          "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js"
        );
      })
      .then(function () {
        return loadScript(
          "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-makefile.min.js"
        );
      })
      .then(function () {
        return loadScript(
          "https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/keep-markup/prism-keep-markup.min.js"
        );
      })
      .then(function () {
        if (window.Prism) {
          window.Prism.highlightAll();
        }
      })
      .catch(function () {
        /* Offline graceful fallback */
      });

    if (document.querySelector("pre.mermaid")) {
      loadScript(
        "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"
      )
        .then(function () {
          if (window.mermaid) {
            window.mermaid.initialize({
              startOnLoad: true,
              theme: "dark",
              securityLevel: "loose"
            });
            window.mermaid.run({ querySelector: "pre.mermaid" });
          }
        })
        .catch(function () {
          /* Offline graceful fallback */
        });
    }
  }

  function initScrollablePreTabindex() {
    var pres = document.querySelectorAll(".code-figure pre");
    pres.forEach(function (pre) {
      if (!pre.hasAttribute("tabindex")) {
        pre.setAttribute("tabindex", "0");
      }
    });
  }

  function normalizeCodeToken(val) {
    return (val || "").trim().replace(/\s+/g, " ");
  }

  function initExercises() {
    var exercises = document.querySelectorAll(".exercise-panel");
    exercises.forEach(function (panel) {
      var inputs = panel.querySelectorAll("input.code-blank");
      var checkBtn = panel.querySelector('[data-action="check"]');
      var hintBtn = panel.querySelector('[data-action="hint"]');
      var revealBtn = panel.querySelector('[data-action="reveal"]');
      var feedback = panel.querySelector(".lab-feedback");
      var hintText = panel.getAttribute("data-hint") || "";
      var successText = panel.getAttribute("data-success") || "All blanks correct!";

      function showFeedback(kind, html) {
        if (!feedback) return;
        feedback.hidden = false;
        feedback.className = "lab-feedback is-" + kind;
        feedback.textContent = html;
      }

      if (checkBtn) {
        checkBtn.addEventListener("click", function () {
          var allOk = true;
          var firstErrorHint = "";
          inputs.forEach(function (inp) {
            var rawAnswers = (inp.getAttribute("data-answers") || "").split("||");
            var accepted = rawAnswers.map(normalizeCodeToken);
            var userVal = normalizeCodeToken(inp.value);
            if (accepted.indexOf(userVal) !== -1) {
              inp.classList.remove("is-wrong");
              inp.classList.add("is-correct");
              inp.setAttribute("aria-invalid", "false");
            } else {
              allOk = false;
              inp.classList.remove("is-correct");
              inp.classList.add("is-wrong");
              inp.setAttribute("aria-invalid", "true");
              if (!firstErrorHint) {
                firstErrorHint =
                  inp.getAttribute("data-error-hint") ||
                  "Check the syntax for this blank and try again.";
              }
            }
          });
          if (allOk) {
            showFeedback("success", successText);
          } else {
            showFeedback("error", firstErrorHint);
          }
        });
      }

      if (hintBtn) {
        hintBtn.addEventListener("click", function () {
          showFeedback("hint", hintText);
        });
      }

      if (revealBtn) {
        revealBtn.addEventListener("click", function () {
          inputs.forEach(function (inp) {
            var rawAnswers = (inp.getAttribute("data-answers") || "").split("||");
            inp.value = rawAnswers[0] || "";
            inp.classList.remove("is-wrong");
            inp.classList.add("is-correct");
            inp.setAttribute("aria-invalid", "false");
          });
          showFeedback("success", successText);
        });
      }
    });
  }

  function initQuizzes() {
    var quizzes = document.querySelectorAll(".quiz-panel");
    quizzes.forEach(function (quiz) {
      var questions = quiz.querySelectorAll(".quiz-question");
      questions.forEach(function (qEl) {
        var buttons = qEl.querySelectorAll(".quiz-option-btn");
        var feedback = qEl.querySelector(".lab-feedback");
        var wrongHint = qEl.getAttribute("data-wrong-hint") || "";

        buttons.forEach(function (btn) {
          btn.addEventListener("click", function () {
            buttons.forEach(function (b) {
              b.classList.remove("is-correct", "is-wrong");
            });
            var isCorrect = btn.getAttribute("data-correct") === "true";
            var explain = btn.getAttribute("data-explain") || "";
            if (isCorrect) {
              btn.classList.add("is-correct");
              if (feedback) {
                feedback.hidden = false;
                feedback.className = "lab-feedback is-success";
                feedback.textContent = explain;
              }
            } else {
              btn.classList.add("is-wrong");
              if (feedback) {
                feedback.hidden = false;
                feedback.className = "lab-feedback is-error";
                feedback.textContent = explain + (wrongHint ? " (" + wrongHint + ")" : "");
              }
            }
          });
        });
      });
    });
  }

  function initVerifyChecklists() {
    var checkboxes = document.querySelectorAll(".verify-panel input[type='checkbox']");
    checkboxes.forEach(function (cb) {
      var key = "spotykach-verify:" + (cb.id || cb.name);
      try {
        if (localStorage.getItem(key) === "1") {
          cb.checked = true;
        }
      } catch (e) {
        /* ignore storage restrictions */
      }
      cb.addEventListener("change", function () {
        try {
          localStorage.setItem(key, cb.checked ? "1" : "0");
        } catch (e) {
          /* ignore */
        }
      });
    });
  }

  function initSpotykachBootSimulator() {
    var mounts = document.querySelectorAll('[data-widget="spotykach-boot-sim"]');
    mounts.forEach(function (mount) {
      mount.innerHTML =
        '<div class="sim-widget" role="region" aria-label="Spotykach Boot Button and Memory Simulator">' +
        '  <div class="sim-header">' +
        '    <h4>Interactive Simulator: D2 Boot Button &amp; BOOT_SRAM Lifecycle</h4>' +
        '    <span class="lab-badge">STM32H750IB • alt_sram.lds</span>' +
        "  </div>" +
        '  <p style="margin-top:0;font-size:0.9rem;color:var(--text-secondary);">' +
        "    Drag the hold-duration slider and toggle the D2 button state to observe how <code>BootController::Update()</code> arbitrates between normal execution, a soft MCU reset (<code>HAL_NVIC_SystemReset()</code> on release), and entering the Daisy USB DFU bootloader (<code>System::ResetToBootloader()</code> at &ge; 3000 ms)." +
        "  </p>" +
        '  <div class="sim-grid">' +
        '    <div class="sim-card">' +
        '      <h5>1. D2 Pin Input (Active-Low Polarity)</h5>' +
        '      <label for="sim-d2-pressed" style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.65rem;cursor:pointer;">' +
        '        <input type="checkbox" id="sim-d2-pressed" checked />' +
        '        <span>Holding Rear D2 Button (Pin = 0V LOW)</span>' +
        "      </label>" +
        '      <label for="sim-hold-ms" style="display:block;font-size:0.84rem;margin-bottom:0.35rem;">' +
        '        Held Duration: <strong id="sim-hold-label">1200 ms</strong>' +
        "      </label>" +
        '      <input type="range" id="sim-hold-ms" min="0" max="4000" step="100" value="1200" style="width:100%;" />' +
        "    </div>" +
        '    <div class="sim-card">' +
        '      <h5>2. BootController State Decision</h5>' +
        '      <div class="sim-readout" id="sim-action-readout"></div>' +
        "    </div>" +
        '    <div class="sim-card">' +
        '      <h5>3. Active STM32H750 Memory Region</h5>' +
        '      <div class="sim-readout" id="sim-mem-readout"></div>' +
        "    </div>" +
        "  </div>" +
        "</div>";

      var pressedCb = mount.querySelector("#sim-d2-pressed");
      var holdSlider = mount.querySelector("#sim-hold-ms");
      var holdLabel = mount.querySelector("#sim-hold-label");
      var actionReadout = mount.querySelector("#sim-action-readout");
      var memReadout = mount.querySelector("#sim-mem-readout");

      function renderSim() {
        var pressed = pressedCb.checked;
        var heldMs = parseInt(holdSlider.value, 10);
        holdLabel.textContent = heldMs + " ms";

        if (pressed && heldMs >= 3000) {
          actionReadout.innerHTML =
            '<strong style="color:var(--accent-secondary);">BootAction::EnterDfuBootloader</strong><br/>' +
            "<code>held_ms &gt;= 3000</code> in <code>AppImpl::Loop()</code><br/>" +
            "Calls <code>System::ResetToBootloader(DAISY_INFINITE_TIMEOUT)</code>";
          memReadout.innerHTML =
            "<strong>Internal Flash (<code>0x08000000</code>)</strong><br/>" +
            "Running <code>bootloader-spotykach-v2.bin</code>.<br/>" +
            "Bottom pad LEDs breathe white; ready for <code>make program-dfu</code> → QSPI (<code>0x90040000</code>).";
        } else if (!pressed && heldMs > 0 && heldMs < 3000) {
          actionReadout.innerHTML =
            '<strong style="color:var(--accent-warn);">BootAction::SystemReset</strong><br/>' +
            "Falling edge detected (<code>!pressed &amp;&amp; was_pressed_</code>)<br/>" +
            "Calls <code>HAL_NVIC_SystemReset()</code> in <code>ProcessDigitalControls()</code>";
          memReadout.innerHTML =
            "<strong>QSPI (<code>0x90040000</code>) → SRAM_EXEC (<code>0x24000000</code>)</strong><br/>" +
            "Bootloader re-copies firmware into 256 KB AXI SRAM and restarts <code>main()</code>.";
        } else {
          actionReadout.innerHTML =
            '<strong style="color:var(--accent-success);">BootAction::None (Normal Run)</strong><br/>' +
            (pressed
              ? "Button held (" + (3000 - heldMs) + " ms until DFU threshold)"
              : "Button idle (Pin D2 = 3.3V HIGH)");
          memReadout.innerHTML =
            "<strong>SRAM_EXEC (<code>0x24000000</code>) + DTCMRAM (<code>0x20000000</code>)</strong><br/>" +
            "Executing <code>AppImpl::Loop()</code> at 480 MHz with zero-wait DTCM stack.";
        }
      }

      pressedCb.addEventListener("change", renderSim);
      holdSlider.addEventListener("input", renderSim);
      renderSim();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initScrollablePreTabindex();
    initExercises();
    initQuizzes();
    initVerifyChecklists();
    initSpotykachBootSimulator();
    initPrismAndMermaid();
  });
})();
