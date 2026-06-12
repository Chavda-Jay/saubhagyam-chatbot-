// ══════════════════════════════════════════════════
//   SAUBHAGYAM ChatBot v2 — app.js
// ══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

    // ── Element References ────────────────────────
    const launcher = document.getElementById('chatLauncher');
    const widget = document.getElementById('chatbotWidget');
    const chatWindow = document.getElementById('chatWindow');
    const userInput = document.getElementById('userInput');
    const typingIndicator = document.getElementById('typingIndicator');
    const quickChips = document.getElementById('quickChips');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const attachBtn = document.getElementById('attachBtn');
    const emojiBtn = document.getElementById('emojiBtn');
    const emojiPicker = document.getElementById('emojiPicker');
    const fileInput = document.getElementById('fileInput');
    const imagePreviewBar = document.getElementById('imagePreviewBar');
    const imageThumb = document.getElementById('imageThumb');
    const imageFileName = document.getElementById('imageFileName');
    const removeImageBtn = document.getElementById('removeImage');
    const clearBtn = document.getElementById('clearBtn');
    const closeBtn = document.getElementById('closeBtn');
    const humanBtn = document.getElementById('humanBtn');

    // Modals
    const bookingModal = document.getElementById('bookingModal');
    const closeBookingModal = document.getElementById('closeBookingModal');
    const submitBookingBtn = document.getElementById('submitBookingBtn');
    const rescheduleModal = document.getElementById('rescheduleModal');
    const closeRescheduleModal = document.getElementById('closeRescheduleModal');
    const submitRescheduleBtn = document.getElementById('submitRescheduleBtn');
    const handoffModal = document.getElementById('handoffModal');
    const closeHandoffModal = document.getElementById('closeHandoffModal');
    const submitHandoffBtn = document.getElementById('submitHandoffBtn');

    // ── State ─────────────────────────────────────
    let selectedFile = null;
    let isRecording = false;
    let recognition = null;

    // ── Chat Persistence (sessionStorage) ─────────
    const CHAT_STORAGE_KEY = 'saubhagyam_chat_messages';

    function saveChatToStorage() {
        const messages = [];
        chatWindow.querySelectorAll('.user-msg, .ai-msg, .follow-chips').forEach(el => {
            if (el.classList.contains('follow-chips')) return; // skip follow chips, they get re-added
            if (el.classList.contains('image-msg')) {
                // Can't persist blob URLs, save a placeholder
                messages.push({
                    type: el.classList.contains('user-msg') ? 'user' : 'ai',
                    isImage: true,
                    html: '<p style="opacity:0.6;"><em>📷 Image (not available after refresh)</em></p>'
                });
            } else if (el.classList.contains('user-msg')) {
                messages.push({ type: 'user', text: el.textContent });
            } else if (el.classList.contains('ai-msg')) {
                messages.push({ type: 'ai', html: el.innerHTML });
            }
        });
        try {
            sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
        } catch (e) {
            // Storage full or unavailable — silently ignore
        }
    }

    function restoreChatFromStorage() {
        try {
            const raw = sessionStorage.getItem(CHAT_STORAGE_KEY);
            if (!raw) return;
            const messages = JSON.parse(raw);
            if (!messages || messages.length === 0) return;

            // Hide quick chips since there's history
            quickChips.style.display = 'none';

            messages.forEach(msg => {
                const div = document.createElement('div');
                if (msg.type === 'user') {
                    div.classList.add('user-msg');
                    if (msg.isImage) {
                        div.classList.add('image-msg');
                        div.innerHTML = msg.html;
                    } else {
                        div.textContent = msg.text;
                    }
                } else {
                    div.classList.add('ai-msg');
                    if (msg.isImage) {
                        div.classList.add('image-msg');
                    }
                    div.innerHTML = msg.html || '';
                }
                chatWindow.appendChild(div);
            });

            // Add follow chips at the end
            addFollowChips();
            scrollBottom();
        } catch (e) {
            // Corrupted data — clear and start fresh
            sessionStorage.removeItem(CHAT_STORAGE_KEY);
        }
    }

    // Restore chat on page load
    restoreChatFromStorage();

    // ══════════════════════════════════════════════
    //   LAUNCHER — Open / Close
    // ══════════════════════════════════════════════
    launcher.addEventListener('click', () => {
        widget.classList.toggle('hidden');
        if (!widget.classList.contains('hidden')) {
            userInput.focus();
        }
    });
    closeBtn.addEventListener('click', () => widget.classList.add('hidden'));

    // ══════════════════════════════════════════════
    //   CLEAR CHAT
    // ══════════════════════════════════════════════
    clearBtn.addEventListener('click', () => {
        chatWindow.querySelectorAll(
            '.user-msg, .ai-msg, .follow-chips, .image-msg'
        ).forEach(el => el.remove());
        quickChips.style.display = 'flex';
        sessionStorage.removeItem(CHAT_STORAGE_KEY);
    });

    // ══════════════════════════════════════════════
    //   QUICK CHIPS
    // ══════════════════════════════════════════════
    quickChips.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.dataset.query;
            if (query === 'BOOK_APPOINTMENT') {
                openModal(bookingModal);
                return;
            }
            quickChips.style.display = 'none';
            sendMessage(query);
        });
    });

    // ══════════════════════════════════════════════
    //   SEND MESSAGE
    // ══════════════════════════════════════════════
    sendBtn.addEventListener('click', handleSend);
    userInput.addEventListener('keypress', e => {
        if (e.key === 'Enter' && !e.shiftKey) handleSend();
    });

    function handleSend() {
        const text = userInput.value.trim();
        if (!text && !selectedFile) return;
        sendMessage(text, selectedFile);
        userInput.value = '';
        clearImagePreview();
    }

    async function sendMessage(text, imageFile = null) {
        // Remove old follow-up chips
        chatWindow.querySelectorAll('.follow-chips').forEach(el => el.remove());

        // Show user message
        if (imageFile) {
            addImageMessage(imageFile, 'user');
        }
        if (text) addMessage(text, 'user');

        quickChips.style.display = 'none';

        // Show typing
        typingIndicator.classList.remove('hidden');
        scrollBottom();

        // try {
        //     // Build FormData (supports text + image)
        //     const formData = new FormData();
        //     formData.append('message', text || 'I sent an image, please analyze it.');
        //     if (imageFile) formData.append('image', imageFile);

        //     // Use streaming endpoint for real-time word-by-word display
        //     const response = await fetch('/chat/stream', {
        //         method: 'POST',
        //         body: formData
        //     });

        //     typingIndicator.classList.add('hidden');

        //     if (!response.ok) {
        //         // Fallback to non-streaming if stream endpoint fails
        //         const fallbackRes = await fetch('/chat', { method: 'POST', body: formData });
        //         const data = await fallbackRes.json();
        //         if (data.action === 'MANAGE_BOOKINGS') {
        //             renderBookingCards(data.bookings);
        //         } else if (data.reply) {
        //             addMessage(data.reply, 'ai');
        //         }
        //         addFollowChips();
        //         return;
        //     }

        //     // Read SSE stream and display tokens word by word
        //     const reader = response.body.getReader();
        //     const decoder = new TextDecoder();
        //     const { element, update } = addStreamingMessage();
        //     let fullReply = '';

        //     while (true) {
        //         const { done, value } = await reader.read();
        //         if (done) break;

        //         const chunk = decoder.decode(value, { stream: true });
        //         const lines = chunk.split('\n');

        //         for (const line of lines) {
        //             if (line.startsWith('data: ')) {
        //                 const data = line.slice(6).trim();
        //                 if (data === '[DONE]') break;
        //                 try {
        //                     const parsed = JSON.parse(data);
        //                     if (parsed.token) {
        //                         fullReply += parsed.token;
        //                         update(fullReply);
        //                         scrollBottom();
        //                     }
        //                 } catch (e) {
        //                     // Skip malformed JSON
        //                 }
        //             }
        //         }

        //     // Stream done — remove blinking cursor, render final formatted reply
        //     element.innerHTML = formatAI(fullReply);
        //     }

        //     // Check if reply contains booking actions — handle via non-stream
        //     if (fullReply.includes('[LOOKUP_BOOKING]') ||
        //         fullReply.includes('[SUBMIT_BOOKING]') ||
        //         fullReply.includes('[HANDOFF_REQUESTED]')) {
        //         // Re-send via non-streaming endpoint for server-side processing
        //         element.remove();
        //         const fd2 = new FormData();
        //         fd2.append('message', text || 'I sent an image, please analyze it.');
        //         if (imageFile) fd2.append('image', imageFile);
        //         const res2 = await fetch('/chat', { method: 'POST', body: fd2 });
        //         const data2 = await res2.json();
        //         if (data2.action === 'MANAGE_BOOKINGS') {
        //             renderBookingCards(data2.bookings);
        //         } else if (data2.reply) {
        //             addMessage(data2.reply, 'ai');
        //         }
        //     }

        //     addFollowChips();
        //     saveChatToStorage();

        // } catch (err) {
        //     typingIndicator.classList.add('hidden');
        //     addMessage('Could not connect to the server. Make sure the backend is running.', 'ai');
        //     console.error(err);
        // }
        try {
            // Build FormData (supports text + image)
            const formData = new FormData();
            formData.append('message', text || 'I sent an image, please analyze it.');
            if (imageFile) formData.append('image', imageFile);

            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            typingIndicator.classList.add('hidden');

            const data = await response.json();

            if (data.action === 'MANAGE_BOOKINGS') {
                renderBookingCards(data.bookings);
            } else if (data.reply) {
                addMessage(data.reply, 'ai');
            }

            addFollowChips();
            saveChatToStorage();

        } catch (err) {
            typingIndicator.classList.add('hidden');
            addMessage('Could not connect to the server. Make sure the backend is running.', 'ai');
            console.error(err);
        }
    }

    // ══════════════════════════════════════════════
    //   ADD MESSAGE TO CHAT
    // ══════════════════════════════════════════════
    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.classList.add(sender === 'user' ? 'user-msg' : 'ai-msg');

        if (sender === 'ai') {
            div.innerHTML = formatAI(text);
        } else {
            div.textContent = text;
        }

        animateIn(div);
        chatWindow.appendChild(div);
        scrollBottom();
        saveChatToStorage();
    }

    // Creates a streaming AI message that updates word by word
    function addStreamingMessage() {
        const div = document.createElement('div');
        div.classList.add('ai-msg');
        div.innerHTML = '<span class="streaming-cursor">▊</span>';
        animateIn(div);
        chatWindow.appendChild(div);
        scrollBottom();

        return {
            element: div,
            update: (text) => {
                div.innerHTML = formatAI(text) + '<span class="streaming-cursor">▊</span>';
            }
        };
    }

    function addImageMessage(file, sender) {
        const wrapper = document.createElement('div');
        wrapper.classList.add(sender === 'user' ? 'user-msg' : 'ai-msg', 'image-msg');
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.style.maxWidth = '180px';
        img.style.borderRadius = '10px';
        wrapper.appendChild(img);
        animateIn(wrapper);
        chatWindow.appendChild(wrapper);
        scrollBottom();
        saveChatToStorage();
    }

    // ══════════════════════════════════════════════
    //   FORMAT AI REPLY (markdown-like)
    // ══════════════════════════════════════════════
    function formatAI(text) {
        // Links: [text](url)
        let html = text.replace(
            /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener">$1</a>'
        );
        // Bold: **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        const lines = html.split('\n');
        let result = '';
        let inList = false;

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) {
                if (inList) { result += '</ul>'; inList = false; }
                continue;
            }
            const bullet = line.match(/^[•\-\*]\s+(.+)/);
            if (bullet) {
                if (!inList) { result += '<ul>'; inList = true; }
                result += `<li>${bullet[1]}</li>`;
            } else {
                if (inList) { result += '</ul>'; inList = false; }
                result += `<p>${line}</p>`;
            }
        }
        if (inList) result += '</ul>';
        return result;
    }

    // ══════════════════════════════════════════════
    //   FOLLOW-UP CHIPS (after each AI reply)
    // ══════════════════════════════════════════════
    function addFollowChips() {
        chatWindow.querySelectorAll('.follow-chips').forEach(el => el.remove());

        const chips = [
            { label: '🤖 AI Services', query: 'Tell me about AI services' },
            { label: '⛓️ Blockchain', query: 'Tell me about Blockchain services' },
            { label: '🛡️ Cybersecurity', query: 'Tell me about Cybersecurity services' },
            { label: '📈 Algo Trading', query: 'Tell me about Algo Trading' },
            { label: '📅 Book Appointment', query: 'BOOK_APPOINTMENT' },
            { label: '⚙️ Manage Booking', query: 'I want to manage my booking' },
            { label: '👤 Talk to Human', query: 'HANDOFF' },
        ];

        const div = document.createElement('div');
        div.classList.add('follow-chips');

        chips.forEach(c => {
            const btn = document.createElement('button');
            btn.classList.add('chip');
            btn.textContent = c.label;
            btn.addEventListener('click', () => {
                if (c.query === 'BOOK_APPOINTMENT') { openModal(bookingModal); return; }
                if (c.query === 'HANDOFF') { openModal(handoffModal); return; }
                sendMessage(c.query);
            });
            div.appendChild(btn);
        });

        animateIn(div);
        chatWindow.appendChild(div);
        scrollBottom();
    }

    // ══════════════════════════════════════════════
    //   RENDER BOOKING MANAGEMENT CARDS
    // ══════════════════════════════════════════════
    function renderBookingCards(bookings) {
        if (!bookings || bookings.length === 0) {
            addMessage('No active bookings found for that email.', 'ai');
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.classList.add('ai-msg');

        const intro = document.createElement('p');
        intro.textContent = 'Here are your active bookings:';
        intro.style.marginBottom = '10px';
        wrapper.appendChild(intro);

        bookings.forEach(b => {
            const card = document.createElement('div');
            card.classList.add('booking-card');
            card.id = `card-${b.id}`;
            card.innerHTML = `
                <p><strong>ID:</strong> ${b.id.slice(0, 8)}...</p>
                <p><strong>Date:</strong> ${b.date}</p>
                <p><strong>Time:</strong> ${b.time}</p>
                <p><strong>Status:</strong> ${b.status}</p>
                <div class="booking-card-actions">
                    <button class="btn-cancel-booking">✕ Cancel</button>
                    <button class="btn-reschedule-booking">↻ Reschedule</button>
                </div>`;

            // Cancel
            card.querySelector('.btn-cancel-booking').addEventListener('click', async () => {
                if (!confirm('Are you sure you want to cancel this appointment?')) return;
                try {
                    const res = await fetch('/api/bookings/cancel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ booking_id: b.id })
                    });
                    const result = await res.json();
                    if (result.success) {
                        addMessage(`Your appointment on ${b.date} has been cancelled successfully.`, 'ai');
                        card.style.opacity = '0.5';
                        card.querySelector('.booking-card-actions').remove();
                    }
                } catch (e) {
                    addMessage('Failed to cancel. Please try again.', 'ai');
                }
            });

            // Reschedule
            card.querySelector('.btn-reschedule-booking').addEventListener('click', () => {
                document.getElementById('rescheduleBookingId').value = b.id;
                openModal(rescheduleModal);
            });

            wrapper.appendChild(card);
        });

        animateIn(wrapper);
        chatWindow.appendChild(wrapper);
        scrollBottom();
    }

    // ══════════════════════════════════════════════
    //   VOICE INPUT (Web Speech API)
    // ══════════════════════════════════════════════
    micBtn.addEventListener('click', () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            addMessage('Voice input is not supported in this browser. Please use Chrome or Edge.', 'ai');
            return;
        }

        if (isRecording) {
            recognition && recognition.stop();
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'en-IN';   // supports English + Indian accent
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('mic-active');
            micBtn.title = 'Listening... click to stop';
        };

        recognition.onresult = (e) => {
            const transcript = e.results[0][0].transcript;
            userInput.value = transcript;
            userInput.focus();
            handleSend();
        };

        recognition.onend = () => {
            isRecording = false;
            micBtn.classList.remove('mic-active');
            micBtn.title = 'Voice Input';
        };

        recognition.onerror = (e) => {
            isRecording = false;
            micBtn.classList.remove('mic-active');
            if (e.error !== 'no-speech') {
                addMessage(`Voice error: ${e.error}. Please try again.`, 'ai');
            }
        };

        recognition.start();
    });

    // ══════════════════════════════════════════════
    //   IMAGE ATTACH
    // ══════════════════════════════════════════════
    attachBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file (JPG, PNG, GIF, WebP).');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            alert('Image size must be under 5MB.');
            return;
        }
        selectedFile = file;
        imageThumb.src = URL.createObjectURL(file);
        imageFileName.textContent = file.name;
        imagePreviewBar.classList.remove('hidden');
        fileInput.value = '';
    });

    removeImageBtn.addEventListener('click', clearImagePreview);

    function clearImagePreview() {
        selectedFile = null;
        imageThumb.src = '';
        imagePreviewBar.classList.add('hidden');
    }

    // ══════════════════════════════════════════════
    //   EMOJI PICKER
    // ══════════════════════════════════════════════
    const EMOJIS = ['😊', '🤝', '🚀', '💻', '✨', '🔥', '✅', '👋', '🤖', '📊',
        '💡', '🛡️', '🌍', '📱', '📧', '⛓️', '🪙', '📈', '🔐', '🎯'];

    EMOJIS.forEach(emoji => {
        const span = document.createElement('span');
        span.classList.add('emoji-item');
        span.textContent = emoji;
        span.addEventListener('click', () => {
            userInput.value += emoji;
            userInput.focus();
            emojiPicker.classList.add('hidden');
        });
        emojiPicker.appendChild(span);
    });

    emojiBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        emojiPicker.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
        if (!emojiPicker.contains(e.target) && e.target !== emojiBtn) {
            emojiPicker.classList.add('hidden');
        }
    });

    // ══════════════════════════════════════════════
    //   LIVE AGENT HANDOFF BUTTON (header)
    // ══════════════════════════════════════════════
    humanBtn.addEventListener('click', () => openModal(handoffModal));

    // ══════════════════════════════════════════════
    //   SLOT BUTTON CLICK HANDLERS
    // ══════════════════════════════════════════════
    function setupSlotButtons(containerSelector, hiddenInputId) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        container.querySelectorAll('.slot-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Deselect all siblings in this modal
                container.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById(hiddenInputId).value = btn.dataset.time;
            });
        });
    }

    // Booking modal slots
    setupSlotButtons('#bookingModal .modal-form', 'bSelectedTime');
    // Reschedule modal slots
    setupSlotButtons('#rescheduleModal .modal-form', 'rSelectedTime');

    // ══════════════════════════════════════════════
    //   BOOKING MODAL — Submit
    // ══════════════════════════════════════════════
    closeBookingModal.addEventListener('click', () => closeModal(bookingModal));

    submitBookingBtn.addEventListener('click', () => {
        const name = document.getElementById('bName').value.trim();
        const email = document.getElementById('bEmail').value.trim();
        const phone = document.getElementById('bPhone').value.trim();
        const service = document.getElementById('bService').value;
        const rawDate = document.getElementById('bDate').value;
        const time = document.getElementById('bSelectedTime').value;

        if (!name || !email || !phone || !service || !rawDate || !time) {
            alert('Please fill in all fields and select a time slot.'); return;
        }

        // Past date check
        const dateObj = new Date(rawDate);
        const today = new Date(); today.setHours(0, 0, 0, 0);
        if (dateObj < today) {
            alert('Cannot book a past date. Please choose today or a future date.'); return;
        }

        // Weekend check
        const day = dateObj.getDay();
        if (day === 0 || day === 6) {
            alert('We are only available Monday to Friday. Please choose a weekday.'); return;
        }

        // Format date
        const date = dateObj.toLocaleDateString('en-GB');

        closeModal(bookingModal);

        // Show user summary in chat
        addMessage(
            `Booking request submitted:\nName: ${name}\nEmail: ${email}\nPhone: ${phone}\nService: ${service}\nDate: ${date}\nTime: ${time}`,
            'user'
        );

        // Internal prompt to AI backend
        const prompt = `[SYSTEM MESSAGE]: User submitted booking via form.\nName: ${name}\nEmail: ${email}\nPhone: ${phone}\nService: ${service}\nDate: ${date}\nTime: ${time}\nPlease confirm the details clearly and end your reply with [SUBMIT_BOOKING]`;

        typingIndicator.classList.remove('hidden');
        scrollBottom();

        const fd = new FormData();
        fd.append('message', prompt);

        fetch('/chat', { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                typingIndicator.classList.add('hidden');
                if (data.reply) {
                    addMessage(data.reply, 'ai');
                    addFollowChips();
                    saveChatToStorage();
                }
            })
            .catch(() => {
                typingIndicator.classList.add('hidden');
                addMessage('Could not connect to server.', 'ai');
            });
    });

    // ══════════════════════════════════════════════
    //   RESCHEDULE MODAL — Submit
    // ══════════════════════════════════════════════
    closeRescheduleModal.addEventListener('click', () => closeModal(rescheduleModal));

    submitRescheduleBtn.addEventListener('click', async () => {
        const bookingId = document.getElementById('rescheduleBookingId').value;
        const rawDate = document.getElementById('rDate').value;
        const time = document.getElementById('rSelectedTime').value;

        if (!rawDate || !time) {
            alert('Please select a date and time slot.'); return;
        }

        const dateObj = new Date(rawDate);
        const today = new Date(); today.setHours(0, 0, 0, 0);
        if (dateObj < today) {
            alert('Cannot reschedule to a past date.'); return;
        }

        const day = dateObj.getDay();
        if (day === 0 || day === 6) {
            alert('Only Monday to Friday available.'); return;
        }

        const date = dateObj.toLocaleDateString('en-GB');

        closeModal(rescheduleModal);

        try {
            const res = await fetch('/api/bookings/reschedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ booking_id: bookingId, new_date: date, new_time: time })
            });
            const result = await res.json();
            if (result.success) {
                addMessage(`Your appointment has been requested to reschedule to ${date} at ${time}. Admin will confirm shortly.`, 'ai');
                // Update card UI
                const card = document.getElementById(`card-${bookingId}`);
                if (card) {
                    card.style.opacity = '0.6';
                    card.querySelector('.booking-card-actions') &&
                        card.querySelector('.booking-card-actions').remove();
                }
            }
        } catch (e) {
            addMessage('Failed to reschedule. Please try again.', 'ai');
        }
    });

    // ══════════════════════════════════════════════
    //   LIVE AGENT HANDOFF MODAL — Submit
    // ══════════════════════════════════════════════
    closeHandoffModal.addEventListener('click', () => closeModal(handoffModal));

    submitHandoffBtn.addEventListener('click', async () => {
        const name = document.getElementById('hName').value.trim();
        const contact = document.getElementById('hContact').value.trim();
        const message = document.getElementById('hMessage').value.trim();

        if (!name || !contact) {
            alert('Please provide your name and contact details.'); return;
        }

        closeModal(handoffModal);

        try {
            const res = await fetch('/api/handoff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, contact, message })
            });
            const result = await res.json();
            if (result.success) {
                addMessage(
                    `✅ Done, ${name}! Our team has been notified and will contact you at "${contact}" within 15 minutes via WhatsApp or Email. 🙏`,
                    'ai'
                );
            }
        } catch (e) {
            addMessage('Failed to connect. Please email us at info@saubhagyam.com', 'ai');
        }

        // Clear form
        document.getElementById('hName').value = '';
        document.getElementById('hContact').value = '';
        document.getElementById('hMessage').value = '';
    });

    // ══════════════════════════════════════════════
    //   HELPERS
    // ══════════════════════════════════════════════
    function openModal(modal) {
        modal.classList.remove('hidden');
    }
    function closeModal(modal) {
        modal.classList.add('hidden');
    }
    function scrollBottom() {
        setTimeout(() => {
            chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
        }, 60);
    }
    function animateIn(el) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(10px)';
        requestAnimationFrame(() => {
            el.style.transition = 'all 0.3s ease-out';
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        });
    }

}); // end DOMContentLoaded