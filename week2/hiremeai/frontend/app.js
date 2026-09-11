/* ============================================================
   HireMeAI — Frontend Application
   ============================================================ */


/* ================= CONFIGURATION ================= */

// FastAPI backend
const API_URL = "http://127.0.0.1:8000";


/* ================= DOM ELEMENTS ================= */

const messagesContainer =
    document.getElementById("messages");

const questionInput =
    document.getElementById("questionInput");

const sendButton =
    document.getElementById("sendButton");

const typingIndicator =
    document.getElementById("typingIndicator");

const characterCount =
    document.getElementById("characterCount");

const quickCards =
    document.querySelectorAll(".quick-card");


/* ================= STATE ================= */

let isLoading = false;


/* ================= ADD MESSAGE ================= */

function addMessage(message, sender = "ai") {

    const messageElement =
        document.createElement("div");

    messageElement.className =
        sender === "user"
            ? "message user-message"
            : "message ai-message";


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        sender === "user"
            ? "You"
            : "H";


    const content =
        document.createElement("div");

    content.className =
        "message-content";


    const meta =
        document.createElement("div");

    meta.className =
        "message-meta";

    meta.innerHTML =
        sender === "user"
            ? "You"
            : "HireMeAI <span>•</span> AI Assistant";


    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";

    bubble.textContent =
        message;


    content.appendChild(meta);
    content.appendChild(bubble);

    messageElement.appendChild(avatar);
    messageElement.appendChild(content);

    messagesContainer.appendChild(messageElement);

    scrollMessagesToBottom();
}


/* ================= SCROLL ================= */

function scrollMessagesToBottom() {

    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: "smooth"
    });

}


/* ================= TYPING ================= */

function setLoading(state) {

    isLoading = state;

    sendButton.disabled = state;

    questionInput.disabled = state;

    if (state) {

        typingIndicator.classList.remove(
            "hidden"
        );

        scrollMessagesToBottom();

    } else {

        typingIndicator.classList.add(
            "hidden"
        );

    }

}


/* ================= SEND MESSAGE ================= */

async function sendMessage(question = null) {

    if (isLoading) {
        return;
    }


    const userQuestion =
        question !== null
            ? question.trim()
            : questionInput.value.trim();


    if (!userQuestion) {
        return;
    }


    if (userQuestion.length > 1000) {

        addMessage(
            "Please keep your question under 1000 characters.",
            "ai"
        );

        return;
    }


    // Display user's question
    addMessage(
        userQuestion,
        "user"
    );


    // Clear input
    questionInput.value = "";

    updateCharacterCount();

    autoResizeTextarea();


    setLoading(true);


    try {

        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        question: userQuestion
                    })
                }
            );


        if (!response.ok) {

            let errorMessage =
                `Backend returned HTTP ${response.status}.`;

            try {

                const errorData =
                    await response.json();

                if (errorData.detail) {
                    errorMessage =
                        errorData.detail;
                }

            } catch {
                // Ignore JSON parsing failure
            }

            throw new Error(errorMessage);
        }


        const data =
            await response.json();


        if (!data.answer) {

            throw new Error(
                "The backend returned no answer."
            );

        }


        addMessage(
            data.answer,
            "ai"
        );


    } catch (error) {

        console.error(
            "HireMeAI request failed:",
            error
        );


        addMessage(
            getFriendlyErrorMessage(error),
            "ai"
        );


    } finally {

        setLoading(false);

        questionInput.disabled = false;

        questionInput.focus();

    }

}


/* ================= ERROR MESSAGE ================= */

function getFriendlyErrorMessage(error) {

    if (
        error instanceof TypeError &&
        error.message.includes("fetch")
    ) {

        return (
            "I couldn't connect to the HireMeAI backend. " +
            "Make sure your FastAPI server is running on " +
            "http://127.0.0.1:8000."
        );

    }


    return (
        "Something went wrong while contacting HireMeAI. " +
        "Please check the backend terminal and try again."
    );

}


/* ================= CHARACTER COUNT ================= */

function updateCharacterCount() {

    const length =
        questionInput.value.length;

    characterCount.textContent =
        `${length} / 1000`;

}


/* ================= TEXTAREA RESIZE ================= */

function autoResizeTextarea() {

    questionInput.style.height =
        "auto";

    questionInput.style.height =
        `${Math.min(
            questionInput.scrollHeight,
            140
        )}px`;

}


/* ================= QUICK QUESTIONS ================= */

quickCards.forEach(card => {

    card.addEventListener(
        "click",
        () => {

            const question =
                card.dataset.question;

            sendMessage(question);

        }
    );

});


/* ================= KEYBOARD ================= */

questionInput.addEventListener(
    "keydown",
    event => {

        /*
         * Enter = send
         * Shift + Enter = new line
         */

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();

        }

    }
);


/* ================= INPUT EVENTS ================= */

questionInput.addEventListener(
    "input",
    () => {

        updateCharacterCount();

        autoResizeTextarea();

    }
);


/* ================= SEND BUTTON ================= */

sendButton.addEventListener(
    "click",
    () => {

        sendMessage();

    }
);


/* ================= INITIALIZATION ================= */

updateCharacterCount();

autoResizeTextarea();

questionInput.focus();