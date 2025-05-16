// static/js/script.js
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Loaded. Initializing CTF script (No Diff Highlighting)...");

    // --- DOM Element Selectors ---
    const difficultySelect = document.getElementById('difficulty-select');
    const challengeControlsDiv = document.querySelector('.challenge-controls');
    const challengeIdDisplaySpan = document.querySelector('#challenge-id-display span');
    const loadingMessage = document.getElementById('loading-message');
    const errorMessage = document.getElementById('error-message');
    // const challengeSelectionSection = document.getElementById('challenge-selection'); // Not used, can be removed
    const challengeArea = document.getElementById('challenge-area');
    const assessmentArea = document.getElementById('assessment-area');
    const resultsArea = document.getElementById('results-area');
    const challengeIdInput = document.getElementById('challenge-id');
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

    const newChallengeBtn = document.createElement('button');
    newChallengeBtn.id = 'new-challenge-btn';
    newChallengeBtn.textContent = 'New Challenge';
    newChallengeBtn.className = 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-medium px-4 py-1.5 rounded-md text-sm transition duration-150 ease-in-out';

    if (challengeControlsDiv) {
        challengeControlsDiv.appendChild(newChallengeBtn);
    } else {
        console.error("Could not find .challenge-controls div.");
    }

    // --- State Variables ---
    let currentChallengeId = null;
    let currentDifficulty = null; // To store the current difficulty
    let correctCweId = null;
    let correctCweName = null;
    let usedDiff = false;
    let originalVulnerableCode = '';
    // let isDiffVisible = false; // Not strictly needed if data-toggled is used
    let fetchedFixedCode = null; // Store fetched fixed code to avoid re-fetching
    const PENALTY_DIFF = -5; // Should be passed from server or defined consistently

    // --- Helper Functions ---
    function showLoading(isLoading) { loadingMessage.classList.toggle('hidden', !isLoading); }
    function showError(message) {
        console.error("Displaying Error:", message);
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }
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
        // currentChallengeId = null; // Don't reset currentChallengeId here, it's set by loadChallenge
        // correctCweId = null; // Reset by loadChallenge
        // correctCweName = null; // Reset by loadChallenge
        originalVulnerableCode = '';
        // isDiffVisible = false; // Reset by diffBtn logic
        fetchedFixedCode = null; // Reset fetched fixed code

        if (diffBtn) {
            diffBtn.disabled = false;
            const penaltyPoints = Math.abs(PENALTY_DIFF);
            diffBtn.textContent = `Show Diff View (-${penaltyPoints} pts)`;
            diffBtn.setAttribute('data-toggled', 'false');
        }
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Assessment";
        }

        if (codeComparisonContainer) codeComparisonContainer.classList.remove('diff-view-mode');
        if (codeComparisonContainer) codeComparisonContainer.classList.add('code-view-mode'); // Ensure it's in single view mode
        if (fixedCodePane) fixedCodePane.classList.add('hidden');
        if (codeBlock) codeBlock.textContent = ''; // Clear old code
        if (fixedCodeBlock) fixedCodeBlock.innerHTML = ''; // Clear old fixed code
        if (codeViewTitle) codeViewTitle.textContent = 'Source Code';

        // Reset Prism classes if they were modified
        if (codeDisplayPre) codeDisplayPre.className = 'language-c line-numbers !m-0 !shadow-none border border-slate-700/50 !rounded-lg relative';
        if (codeBlock) codeBlock.className = 'language-c';
        if (fixedCodeDisplayPre) fixedCodeDisplayPre.className = 'language-c line-numbers !m-0 !shadow-none border border-slate-700/50 !rounded-lg relative';
        if (fixedCodeBlock) fixedCodeBlock.className = 'language-c';


        if (assessmentArea) assessmentArea.classList.add('hidden');
        if (resultsArea) resultsArea.classList.add('hidden');
        if (feedbackMessage) feedbackMessage.textContent = '';
        if (scoreBreakdownP) scoreBreakdownP.textContent = '';
        
        const correctAnswerSpan = correctAnswerP ? correctAnswerP.querySelector('span') : null;
        if (correctAnswerSpan) correctAnswerSpan.textContent = '';
        else if (correctAnswerP) correctAnswerP.innerHTML = 'Correct Vulnerability Type: <span class="ml-1 font-mono bg-slate-700 px-2 py-0.5 rounded text-indigo-300"></span>';
        
        if (solutionExplanationDiv) solutionExplanationDiv.textContent = '';
        if (challengeIdDisplaySpan) challengeIdDisplaySpan.textContent = 'Loading...';

        if (vulnerabilitySelect) {
            vulnerabilitySelect.selectedIndex = 0; // Reset dropdown
        }
        // hideError(); // Error is hidden at the start of loadChallenge
    }

    // --- Core Logic ---
    async function loadChallenge(difficulty) {
        console.log(`Loading challenge for difficulty: ${difficulty}`);
        resetUIState(); // Reset UI elements before loading new challenge
        showLoading(true);
        hideError(); // Clear previous errors explicitly at the start

        try {
            const cacheBuster = `?t=${Date.now()}`; // Prevent caching issues
            const response = await fetch(`/get_challenge/${difficulty}${cacheBuster}`);

            if (!response.ok) {
                let errorMsgToShow;
                // Try to parse the error response as JSON, as our app.py 404/error might send JSON
                try {
                    const errorData = await response.json();
                    errorMsgToShow = errorData.error || `Error: ${response.statusText} (Status: ${response.status})`;
                } catch (e) {
                    // If error response is not JSON (e.g., HTML error page from proxy/server)
                    errorMsgToShow = `Failed to load challenge. Server returned: ${response.status} ${response.statusText}`;
                }
                
                showError(errorMsgToShow);
                challengeArea.classList.add('hidden'); // Hide challenge area on error
                assessmentArea.classList.add('hidden');
                resultsArea.classList.add('hidden');
                showLoading(false); // Hide loading indicator
                return; // Stop further processing
            }

            // If response.ok is true, then expect valid JSON challenge data
            const data = await response.json(); // This might throw if body is not JSON

            if (!data || typeof data.id === 'undefined' || typeof data.vulnerable_code === 'undefined' || typeof data.correct_cwe === 'undefined') {
                console.error("Invalid challenge data structure received:", data);
                throw new Error("Invalid challenge data format from server.");
            }
            console.log("Challenge data received:", data);

            // Update state variables
            currentChallengeId = data.id;
            currentDifficulty = data.difficulty;
            correctCweId = data.correct_cwe;
            correctCweName = data.correct_cwe_name;
            originalVulnerableCode = data.vulnerable_code;
            // fetchedFixedCode = null; // Already reset in resetUIState

            // Update UI
            if (challengeIdInput) challengeIdInput.value = currentChallengeId;
            if (challengeIdDisplaySpan) challengeIdDisplaySpan.textContent = currentChallengeId;
            if (codeBlock) codeBlock.textContent = originalVulnerableCode;
            
            // Ensure Prism highlights the new code
            if (codeBlock && Prism) {
                 Prism.highlightElement(codeBlock);
            }

            if (challengeArea) challengeArea.classList.remove('hidden');
            if (assessmentArea) assessmentArea.classList.remove('hidden');
            if (resultsArea) resultsArea.classList.add('hidden'); // Ensure results are hidden
            if (difficultySelect) difficultySelect.value = currentDifficulty;

        } catch (error) { // Catches errors from fetch itself or from response.json() or explicit throws
            console.error("Error in loadChallenge's try-catch block:", error);
            // error.message here might be "JSON.parse: unexpected character..." if response.json() failed on a 200 OK response
            // or "Invalid challenge data format..." from the explicit throw.
            showError(`Failed to load or parse challenge data: ${error.message}`);
            if (challengeArea) challengeArea.classList.add('hidden');
            if (assessmentArea) assessmentArea.classList.add('hidden');
        } finally {
            showLoading(false); // Ensure loading is always hidden
        }
    }

    function showResult(data) {
        console.log("Showing results:", data);
        if (feedbackMessage) {
            feedbackMessage.textContent = data.correct ? 'Correct!' : 'Incorrect!';
            feedbackMessage.className = `text-lg font-semibold mb-4 p-3 rounded-md border ${data.correct ? 'correct' : 'incorrect'}`;
        }
        if (scoreBreakdownP) scoreBreakdownP.textContent = `Score Earned: ${data.score_earned} points.`;

        const correctAnswerDisplaySpan = correctAnswerP ? correctAnswerP.querySelector('span') : null;
        if (correctAnswerDisplaySpan) {
            correctAnswerDisplaySpan.textContent = escapeHtml(data.correct_cwe_name || data.correct_cwe || 'N/A');
        } else if (correctAnswerP) {
             correctAnswerP.innerHTML = `Correct Vulnerability Type: <span class="ml-1 font-mono bg-slate-700 px-2 py-0.5 rounded text-indigo-300">${escapeHtml(data.correct_cwe_name || data.correct_cwe || 'N/A')}</span>`;
        }

        if (solutionExplanationDiv) solutionExplanationDiv.textContent = data.solution || "No solution explanation provided.";
        if (userScoreSpan) userScoreSpan.textContent = data.total_score;
        if (userCompletedSpan) userCompletedSpan.textContent = data.completed_count;

        if (assessmentArea) assessmentArea.classList.add('hidden');
        if (resultsArea) resultsArea.classList.remove('hidden');
        if (diffBtn) diffBtn.disabled = true; // Disable diff button after submission until next challenge
    }

    // --- Event Listeners ---
    if (difficultySelect) {
        difficultySelect.addEventListener('change', () => {
            const selectedDifficulty = difficultySelect.value;
            loadChallenge(selectedDifficulty);
        });
    }

    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            console.log("Submit button clicked.");
            hideError();
            if (!currentChallengeId) { showError("No challenge loaded."); return; }
            const selectedValue = vulnerabilitySelect ? vulnerabilitySelect.value : null;
            if (!selectedValue) { showError("Please select a vulnerability type."); return; }

            const submissionData = {
                challenge_id: currentChallengeId,
                selected_cwe: btoa(selectedValue), // Encode the selected CWE ID
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

                if (response.status === 429) {
                    const retryAfter = response.headers.get('Retry-After');
                    let waitMessage = "You are submitting answers too quickly. Please wait a moment and try again.";
                    if (retryAfter) {
                        waitMessage = `You are submitting answers too quickly. Please try again in ${retryAfter} seconds.`;
                    }
                    showError(waitMessage);
                    // Keep submit button disabled, re-enable after timeout
                    setTimeout(() => {
                        if (submitBtn.disabled && submitBtn.textContent === "Submitting...") { // Check if still in this state
                           submitBtn.disabled = false;
                           submitBtn.textContent = "Submit Assessment";
                        }
                    }, retryAfter ? parseInt(retryAfter) * 1000 + 1000 : 30000); // Add 1s buffer
                    return;
                }

                if (!response.ok) {
                    let errorText = `HTTP error! Status: ${response.status}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorText = errorData.error;
                        }
                    } catch (e) {
                        const text = await response.text();
                        if (text && text.length < 200) errorText = text;
                    }
                    throw new Error(errorText);
                }
                const resultData = await response.json();
                if (typeof resultData.correct === 'undefined' || typeof resultData.score_earned === 'undefined') {
                    console.error("Invalid result data structure:", resultData);
                    throw new Error("Invalid result data from server.");
                }
                showResult(resultData);
            } catch (error) {
                showError(`Error submitting answer: ${error.message}`);
                console.error("Submit error:", error);
                // Re-enable button on other errors
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Assessment";
            }
            // No finally block to re-enable button, handled by specific cases
        });
    }

    if (nextChallengeBtn) {
        nextChallengeBtn.addEventListener('click', () => {
            const difficulty = difficultySelect ? difficultySelect.value : 'easy';
            loadChallenge(difficulty);
        });
    }

    if (newChallengeBtn) {
        newChallengeBtn.addEventListener('click', () => {
            const difficulty = difficultySelect ? difficultySelect.value : 'easy';
            loadChallenge(difficulty);
        });
    }

    if (diffBtn) {
        diffBtn.addEventListener('click', async () => {
            console.log("--- Diff button clicked ---");
            hideError();
            if (!currentChallengeId) { showError("Cannot show diff, no challenge loaded."); return; }

            const currentlyToggled = diffBtn.getAttribute('data-toggled') === 'true';
            diffBtn.disabled = true;
            diffBtn.textContent = 'Loading...';

            try {
                if (!currentlyToggled) { // ---- Switching TO Diff View ----
                    if (!usedDiff) { usedDiff = true; console.log("Marked usedDiff = true for scoring."); }

                    if (fetchedFixedCode === null) { // Fetch only if not already fetched
                        console.log("Diff button: Fetching fixed code...");
                        const diffResponse = await fetch(`/get_diff/${currentChallengeId}`);
                        if (!diffResponse.ok) {
                            let errorText = `Error loading diff data (Status: ${diffResponse.status})`;
                            try { const errData = await diffResponse.json(); if(errData.error) errorText = errData.error; } catch(e){}
                            throw new Error(errorText);
                        }
                        const diffData = await diffResponse.json();
                        if (typeof diffData.fixed_code === 'undefined') throw new Error("Missing 'fixed_code' in diff response.");
                        fetchedFixedCode = diffData.fixed_code;
                    }

                    if (codeBlock) codeBlock.textContent = originalVulnerableCode;
                    if (fixedCodeBlock) fixedCodeBlock.textContent = fetchedFixedCode;

                    if (codeComparisonContainer) {
                        codeComparisonContainer.classList.remove('code-view-mode');
                        codeComparisonContainer.classList.add('diff-view-mode');
                    }
                    if (fixedCodePane) fixedCodePane.classList.remove('hidden');
                    if (codeViewTitle) codeViewTitle.textContent = 'Diff View (Vulnerable vs Fixed)';

                    if (Prism && codeBlock && fixedCodeBlock) {
                        Prism.highlightElement(codeBlock);
                        Prism.highlightElement(fixedCodeBlock);
                    }
                    diffBtn.textContent = 'Show Original Code';
                    diffBtn.setAttribute('data-toggled', 'true');
                } else { // ---- Switching BACK To Original View ----
                    if (codeBlock) codeBlock.textContent = originalVulnerableCode;
                    if (fixedCodeBlock) fixedCodeBlock.innerHTML = ''; // Clear fixed code

                    if (codeComparisonContainer) {
                        codeComparisonContainer.classList.remove('diff-view-mode');
                        codeComparisonContainer.classList.add('code-view-mode');
                    }
                    if (fixedCodePane) fixedCodePane.classList.add('hidden');
                    if (codeViewTitle) codeViewTitle.textContent = 'Source Code';

                    if (Prism && codeBlock) {
                        Prism.highlightElement(codeBlock);
                    }
                    const penaltyPoints = Math.abs(PENALTY_DIFF);
                    diffBtn.textContent = `Show Diff View (-${penaltyPoints} pts)`;
                    diffBtn.setAttribute('data-toggled', 'false');
                }
            } catch (error) {
                showError(`Error toggling diff view: ${error.message}`);
                console.error("Diff button error:", error);
                // Reset to a known state if diff loading fails
                if (codeBlock) codeBlock.textContent = originalVulnerableCode; // Show original
                if (Prism && codeBlock) Prism.highlightElement(codeBlock);
                if (codeComparisonContainer) codeComparisonContainer.classList.add('code-view-mode');
                if (fixedCodePane) fixedCodePane.classList.add('hidden');

                const penaltyPoints = Math.abs(PENALTY_DIFF);
                diffBtn.textContent = `Show Diff View (-${penaltyPoints} pts)`;
                diffBtn.setAttribute('data-toggled', 'false');

            } finally {
                diffBtn.disabled = false; // Re-enable button after operation
            }
        });
    }

    function initializeApp(startDifficulty = 'easy') {
        console.log("Auditor CTF Initializing...");
        hideError();
        if (difficultySelect) {
            difficultySelect.value = startDifficulty;
            loadChallenge(startDifficulty);
        } else {
            console.warn("Difficulty select not found, loading with default if newChallengeBtn exists.");
            if (newChallengeBtn) loadChallenge(startDifficulty); // Fallback if only new challenge button exists
            else showError("Initialization Error: Essential UI components (difficulty select or new challenge button) missing.");
        }
    }

    initializeApp('easy');

});
