// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Initializing CTF script (No Diff Highlighting)...");

    // --- DOM Element Selectors ---
    const difficultySelect = document.getElementById('difficulty-select');
    const challengeControlsDiv = document.querySelector('.challenge-controls'); // Target for button placement
    const challengeIdDisplaySpan = document.querySelector('#challenge-id-display span');
    const loadingMessage = document.getElementById('loading-message');
    const errorMessage = document.getElementById('error-message');
    const challengeSelectionSection = document.getElementById('challenge-selection');
    const challengeArea = document.getElementById('challenge-area');
    const assessmentArea = document.getElementById('assessment-area');
    const resultsArea = document.getElementById('results-area');
    const challengeIdInput = document.getElementById('challenge-id'); // Keep this hidden input
    const codeComparisonContainer = document.getElementById('code-comparison-container');
    const codeViewTitle = document.getElementById('code-view-title');
    const vulnerableCodePane = document.getElementById('vulnerable-code-pane');
    const codeDisplayPre = document.getElementById('code-display');
    const codeBlock = document.getElementById('code-block');
    const fixedCodePane = document.getElementById('fixed-code-pane');
    const fixedCodeDisplayPre = document.getElementById('fixed-code-display');
    const fixedCodeBlock = document.getElementById('fixed-code-block');
    const diffBtn = document.getElementById('diff-btn');
    const vulnerabilitySelect = document.getElementById('vulnerability-select');
    const submitBtn = document.getElementById('submit-btn');
    const feedbackMessage = document.getElementById('feedback-message');
    const scoreBreakdownP = document.getElementById('score-breakdown');
    const correctAnswerP = document.getElementById('correct-answer');
    const solutionExplanationDiv = document.getElementById('solution-explanation');
    const nextChallengeBtn = document.getElementById('next-challenge-btn');
    const userScoreSpan = document.getElementById('user-score');
    const userCompletedSpan = document.getElementById('user-completed');

    // Create New Challenge button
    const newChallengeBtn = document.createElement('button');
    newChallengeBtn.id = 'new-challenge-btn';
    newChallengeBtn.textContent = 'New Challenge';
    // --- ADD Tailwind classes for styling ---
    newChallengeBtn.className = 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium px-4 py-1.5 rounded-md text-sm transition duration-150 ease-in-out'; // Adjusted padding/size

    // Append to the correct div
    if (challengeControlsDiv) {
        challengeControlsDiv.appendChild(newChallengeBtn);
        console.log("New Challenge button appended to .challenge-controls");
    } else {
        console.error("Could not find .challenge-controls div.");
    }

    // --- State Variables ---
    let currentChallengeId = null;
    let currentDifficulty = null;
    let correctCweId = null;
    let correctCweName = null;
    let usedDiff = false;
    let originalVulnerableCode = '';
    let isDiffVisible = false;
    let fetchedFixedCode = null;
    const PENALTY_DIFF = -5;

    // --- Helper Functions ---
    function showLoading(isLoading) { loadingMessage.classList.toggle('hidden', !isLoading); }
    function showError(message) { console.error("Displaying Error:", message); errorMessage.textContent = message; errorMessage.classList.remove('hidden'); }
    function hideError() { errorMessage.classList.add('hidden'); errorMessage.textContent = ''; }
    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        return String(unsafe)
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // --- UI State Management ---
    function resetUIState() {
        console.log("Resetting UI State...");
        usedDiff = false;
        currentChallengeId = null; correctCweId = null; correctCweName = null; originalVulnerableCode = ''; isDiffVisible = false; fetchedFixedCode = null;

        diffBtn.disabled = false;
        const penaltyPoints = Math.abs(PENALTY_DIFF);
        diffBtn.textContent = `Show Diff View (-${penaltyPoints} pts)`;
        diffBtn.setAttribute('data-toggled', 'false');
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Assessment";

        codeComparisonContainer.classList.remove('diff-view-mode');
        codeComparisonContainer.classList.add('code-view-mode');
        fixedCodePane.classList.add('hidden');
        codeBlock.textContent = '';
        fixedCodeBlock.innerHTML = '';
        codeViewTitle.textContent = 'Source Code';

        codeDisplayPre.className = 'language-c line-numbers';
        codeBlock.className = 'language-c';
        fixedCodeDisplayPre.className = 'line-numbers language-c';
        fixedCodeBlock.className = 'language-c';

        assessmentArea.classList.add('hidden'); resultsArea.classList.add('hidden');
        feedbackMessage.textContent = ''; scoreBreakdownP.textContent = '';
        const correctAnswerSpan = correctAnswerP.querySelector('span');
        if (correctAnswerSpan) correctAnswerSpan.textContent = '';
        else correctAnswerP.innerHTML = 'Correct Vulnerability Type: <span></span>';
        solutionExplanationDiv.textContent = '';
        challengeIdDisplaySpan.textContent = 'Loading...';

        if (vulnerabilitySelect) {
            vulnerabilitySelect.selectedIndex = 0;
        }
        hideError();
    }

    // --- Core Logic ---
    async function loadChallenge(difficulty) {
        console.log(`Loading challenge for difficulty: ${difficulty}`);
        resetUIState();
        showLoading(true);

        try {
            const cacheBuster = `?t=${Date.now()}`;
            const response = await fetch(`/get_challenge/${difficulty}${cacheBuster}`);
            showLoading(false);

            if (!response.ok) {
                if (response.status === 404) {
                    const errorData = await response.json().catch(() => ({ error: "No challenges found" }));
                    showError(errorData.error || `No challenges available for ${difficulty}.`);
                    challengeArea.classList.add('hidden');
                    return;
                }
                const errorData = await response.json().catch(() => ({ error: `HTTP error! Status: ${response.status}` }));
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            if (!data || !data.id || !data.vulnerable_code || !data.correct_cwe) {
                 console.error("Invalid challenge data structure:", data);
                throw new Error("Invalid challenge data from server.");
            }
            console.log("Challenge data received:", data);

            // Update state
            currentChallengeId = data.id;
            currentDifficulty = data.difficulty;
            correctCweId = data.correct_cwe;
            correctCweName = data.correct_cwe_name;
            originalVulnerableCode = data.vulnerable_code;

            // UI Update
            challengeIdInput.value = currentChallengeId; // Update hidden input
            challengeIdDisplaySpan.textContent = currentChallengeId; // Update displayed ID
            codeBlock.textContent = originalVulnerableCode;
            codeDisplayPre.className = 'language-c line-numbers';
            codeBlock.className = 'language-c';

            // Highlight syntax
            setTimeout(() => {
                 try { Prism.highlightElement(codeBlock); }
                 catch (e) { console.error("Prism error:", e); showError("Syntax highlighting failed."); }
            }, 50);

            // Show relevant areas
            challengeArea.classList.remove('hidden');
            assessmentArea.classList.remove('hidden');
            resultsArea.classList.add('hidden');
            difficultySelect.value = currentDifficulty;

        } catch (error) {
            showLoading(false);
            if (!errorMessage.textContent.includes("No challenges found")) {
                 showError(`Error fetching challenge: ${error.message}`);
            }
            console.error("Fetch error in loadChallenge:", error);
            challengeArea.classList.add('hidden');
            assessmentArea.classList.add('hidden');
        }
    }

    // --- showResult remains the same ---
     function showResult(data) {
        console.log("Showing results:", data);
        feedbackMessage.textContent = data.correct ? 'Correct!' : 'Incorrect!';
        feedbackMessage.className = data.correct ? 'correct' : 'incorrect';
        scoreBreakdownP.textContent = `Score Earned: ${data.score_earned} points.`;

        const correctAnswerSpan = correctAnswerP.querySelector('span');
        if (correctAnswerSpan) {
            correctAnswerSpan.textContent = escapeHtml(data.correct_cwe_name || data.correct_cwe || 'N/A');
        } else {
             correctAnswerP.innerHTML = `Correct Vulnerability Type: <span>${escapeHtml(data.correct_cwe_name || data.correct_cwe || 'N/A')}</span>`;
        }

        solutionExplanationDiv.textContent = data.solution || "No solution explanation provided.";
        userScoreSpan.textContent = data.total_score;
        userCompletedSpan.textContent = data.completed_count;

        assessmentArea.classList.add('hidden');
        resultsArea.classList.remove('hidden');
        diffBtn.disabled = false;
    }

    // --- Event Listeners ---
     difficultySelect.addEventListener('change', () => {
        const selectedDifficulty = difficultySelect.value;
        hideError();
        loadChallenge(selectedDifficulty);
    });

    submitBtn.addEventListener('click', async () => {
        console.log("Submit button clicked.");
        hideError();
        if (!currentChallengeId) { showError("No challenge loaded."); return; }
        const selectedValue = vulnerabilitySelect.value;
        if (!selectedValue) { showError("Please select a vulnerability type."); return; }

        const submissionData = {
            challenge_id: currentChallengeId,
            selected_cwe: btoa(selectedValue),
            used_diff: usedDiff
        };

        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting...";

        try {
            const response = await fetch('/submit_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(submissionData)
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `HTTP error! Status: ${response.status}` }));
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }
            const resultData = await response.json();
            if (typeof resultData.correct === 'undefined' || typeof resultData.score_earned === 'undefined' || typeof resultData.correct_cwe_name === 'undefined') {
                console.error("Invalid result data structure:", resultData);
                throw new Error("Invalid result data structure.");
            }
            showResult(resultData);
        } catch (error) {
            showError(`Error submitting answer: ${error.message}`);
            console.error("Submit error:", error);
            submitBtn.disabled = false; // Re-enable on error
            submitBtn.textContent = "Submit Assessment";
        }
    });

    nextChallengeBtn.addEventListener('click', () => {
        const difficulty = difficultySelect.value;
        hideError();
        loadChallenge(difficulty);
    });

    newChallengeBtn.addEventListener('click', () => {
        const difficulty = difficultySelect.value;
        hideError();
        loadChallenge(difficulty);
    });


    // --- Diff Button Listener (No Highlighting) ---
    diffBtn.addEventListener('click', async () => {
        console.log("--- Diff button clicked (No Highlighting Version) ---");
        hideError();
        if (!currentChallengeId) { showError("Cannot show diff, no challenge loaded."); return; }

        const currentlyToggled = diffBtn.getAttribute('data-toggled') === 'true';
        diffBtn.disabled = true;
        diffBtn.textContent = 'Loading...';

        if (!currentlyToggled) { // ---- Switching TO Diff View ----
            console.log("Diff button: Switching TO diff view...");
            if (!usedDiff) { usedDiff = true; console.log("Marked usedDiff = true"); }

            try {
                // Fetch fixed code if needed
                if (fetchedFixedCode === null) {
                    console.log("Diff button: Fetching fixed code...");
                    const response = await fetch(`/get_diff/${currentChallengeId}`);
                    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
                    const data = await response.json();
                    if (typeof data.fixed_code === 'undefined') throw new Error("Missing 'fixed_code'.");
                    fetchedFixedCode = data.fixed_code;
                }

                // Set Code Content
                codeBlock.textContent = originalVulnerableCode;
                fixedCodeBlock.textContent = fetchedFixedCode;

                // Ensure Correct Classes for Prism
                codeDisplayPre.className = 'language-c line-numbers';
                fixedCodeDisplayPre.className = 'language-c line-numbers';
                codeBlock.className = 'language-c';
                fixedCodeBlock.className = 'language-c';

                // Update Layout
                codeViewTitle.textContent = 'Diff View (Vulnerable vs Fixed)';
                codeComparisonContainer.classList.remove('code-view-mode');
                codeComparisonContainer.classList.add('diff-view-mode'); // This class enables side-by-side via CSS
                fixedCodePane.classList.remove('hidden');

                // Apply Prism Highlighting to BOTH panes
                console.log("Applying Prism highlighting to diff view...");
                await new Promise(resolve => setTimeout(() => {
                    try {
                        Prism.highlightElement(codeBlock);
                        Prism.highlightElement(fixedCodeBlock);
                        console.log("Prism highlighting applied to diff panes.");
                    } catch (e) {
                        console.error("Prism error on diff:", e);
                        showError("Syntax highlighting failed on diff view.");
                    }
                    resolve();
                }, 50));

                // Update button state
                diffBtn.textContent = 'Show Original Code';
                diffBtn.setAttribute('data-toggled', 'true');
                isDiffVisible = true;

            } catch (error) {
                showError(`Error loading diff: ${error.message}`);
                console.error("Diff error:", error);
                resetUIState();
            } finally {
                diffBtn.disabled = false;
            }

        } else { // ---- Switching BACK To Original View ----
            console.log("Diff button: Switching BACK to original code view...");

            codeBlock.textContent = originalVulnerableCode;
            fixedCodeBlock.innerHTML = '';

            codeDisplayPre.className = 'language-c line-numbers';
            codeBlock.className = 'language-c';
            fixedCodeDisplayPre.className = 'line-numbers language-c';
            fixedCodeBlock.className = 'language-c';

            // Re-highlight original code
            setTimeout(() => {
                 try { Prism.highlightElement(codeBlock); }
                 catch (e) { console.error("Prism error on original:", e); }
             }, 50);

            // Update layout
            codeComparisonContainer.classList.remove('diff-view-mode');
            codeComparisonContainer.classList.add('code-view-mode');
            fixedCodePane.classList.add('hidden');
            codeViewTitle.textContent = 'Source Code';

            // Update button state
            const penaltyPoints = Math.abs(PENALTY_DIFF);
            diffBtn.textContent = `Show Diff View (-${penaltyPoints} pts)`;
            diffBtn.setAttribute('data-toggled', 'false');
            isDiffVisible = false;
            diffBtn.disabled = false;
        }
    });


    // --- Initial Setup Function ---
    function initializeApp(startDifficulty = 'easy') {
        console.log("Auditor CTF Initializing...");
        hideError();
        difficultySelect.value = startDifficulty;
        loadChallenge(startDifficulty);
    }

    // --- Run Initial Setup ---
    if (difficultySelect && vulnerabilitySelect && submitBtn) {
        initializeApp('easy');
    } else {
        console.error("Initialization failed: Missing essential elements.");
        showError("Initialization Error: UI components missing.");
    }

}); // End DOMContentLoaded
