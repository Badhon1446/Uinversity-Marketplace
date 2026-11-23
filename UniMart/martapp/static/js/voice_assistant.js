/**
 * UniMart Voice Assistant Client
 * Architecture:
 * - Speech-to-Text: Browser SpeechRecognition / webkitSpeechRecognition (lang: 'bn-BD')
 * - Text-to-Speech: Browser speechSynthesis / SpeechSynthesisUtterance (lang: 'bn-BD')
 * - Backend: Django API /api/voice-assistant/ (powered by Google Gemini Function Calling)
 */

document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('voice-assistant-container');
  if (!container) return;

  const triggerBtn = document.getElementById('voice-trigger-btn');
  const modal = document.getElementById('voice-modal');
  const modalCloseBtn = document.getElementById('voice-modal-close-btn');
  const pulseRing = document.getElementById('voice-pulse-ring');
  const pulseRing2 = document.getElementById('voice-pulse-ring-2');
  const statusBox = document.getElementById('voice-status-box');
  const statusText = document.getElementById('voice-status-text');
  const statusIcon = document.getElementById('voice-status-icon');
  const userTranscriptContainer = document.getElementById('voice-user-transcript-container');
  const userTranscript = document.getElementById('voice-user-transcript');
  const replyContainer = document.getElementById('voice-assistant-reply-container');
  const replyText = document.getElementById('voice-assistant-reply-text');
  const speakingIcon = document.getElementById('voice-speaking-icon');
  const resultsContainer = document.getElementById('voice-results-container');
  const resultsCount = document.getElementById('voice-results-count');
  const productsGrid = document.getElementById('voice-products-grid');
  const retryBtn = document.getElementById('voice-retry-btn');
  const chips = document.querySelectorAll('.voice-chip');

  // Check Browser Support for SpeechRecognition
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;
  let hasHandledFinalSpeech = false;
  let lastCapturedText = '';

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'bn-BD';
    recognition.continuous = false;
    recognition.interimResults = true; // Show live text as user speaks
    recognition.maxAlternatives = 1;

    recognition.onstart = function () {
      isListening = true;
      hasHandledFinalSpeech = false;
      lastCapturedText = '';
      setListeningState(true);
      setStatus('শুনছি... আপনার প্রশ্ন বা পণ্যের নাম বলুন...', 'listening');
      console.log('SpeechRecognition started (lang: bn-BD)');
    };

    recognition.onresult = function (event) {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      const activeText = (final || interim).trim();
      if (activeText) {
        lastCapturedText = activeText;
        userTranscriptContainer.classList.remove('hidden');
        userTranscript.textContent = activeText;
      }

      if (final && !hasHandledFinalSpeech) {
        hasHandledFinalSpeech = true;
        handleRecognizedSpeech(final.trim());
      }
    };

    recognition.onerror = function (event) {
      isListening = false;
      setListeningState(false);
      console.warn('SpeechRecognition error:', event.error);

      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setStatus('মাইক্রোফোন ব্যবহারের অনুমতি দেওয়া হয়নি।', 'error');
        speakReply('মাইক্রোফোনের অনুমতি প্রয়োজন। ব্রাউজার সেটিংসে গিয়ে অনুমতি দিন।');
      } else if (event.error === 'no-speech') {
        if (!hasHandledFinalSpeech && lastCapturedText) {
          hasHandledFinalSpeech = true;
          handleRecognizedSpeech(lastCapturedText);
        } else {
          setStatus('কোনো শব্দ শোনা যায়নি। আবার চেষ্টা করুন।', 'idle');
        }
      } else {
        setStatus('শব্দ ধারণে সমস্যা হয়েছে। আবার বলুন।', 'error');
      }
    };

    recognition.onend = function () {
      isListening = false;
      setListeningState(false);
      console.log('SpeechRecognition ended.');

      // If speech ended with text but isFinal was not triggered, process it
      if (!hasHandledFinalSpeech && lastCapturedText) {
        hasHandledFinalSpeech = true;
        handleRecognizedSpeech(lastCapturedText);
      }
    };
  }

  // Open / Close Modal
  function openModal() {
    modal.classList.remove('hidden');
    requestAnimationFrame(() => {
      modal.classList.remove('scale-95', 'opacity-0');
      modal.classList.add('scale-100', 'opacity-100');
    });
  }

  function closeModal() {
    stopListening();
    stopSpeaking();
    modal.classList.remove('scale-100', 'opacity-100');
    modal.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
      modal.classList.add('hidden');
    }, 250);
  }

  // Listening State Visuals
  function setListeningState(active) {
    if (active) {
      pulseRing.classList.remove('hidden');
      pulseRing2.classList.remove('hidden');
      triggerBtn.classList.add('ring-4', 'ring-amber-300');
    } else {
      pulseRing.classList.add('hidden');
      pulseRing2.classList.add('hidden');
      triggerBtn.classList.remove('ring-4', 'ring-amber-300');
    }
  }

  // Status message setter
  function setStatus(message, state) {
    statusText.textContent = message;
    statusBox.className = 'flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-lg border';

    if (state === 'listening') {
      statusBox.classList.add('bg-red-50', 'text-red-700', 'border-red-200');
      statusIcon.className = 'fa-solid fa-microphone text-red-500 animate-pulse';
    } else if (state === 'processing') {
      statusBox.classList.add('bg-blue-50', 'text-blue-700', 'border-blue-200');
      statusIcon.className = 'fa-solid fa-spinner fa-spin text-blue-500';
    } else if (state === 'error') {
      statusBox.classList.add('bg-rose-50', 'text-rose-700', 'border-rose-200');
      statusIcon.className = 'fa-solid fa-triangle-exclamation text-rose-500';
    } else {
      statusBox.classList.add('bg-amber-50', 'text-amber-800', 'border-amber-200');
      statusIcon.className = 'fa-solid fa-circle-info text-amber-600';
    }
  }

  // Start / Stop listening
  function startListening() {
    if (!SpeechRecognition) {
      openModal();
      setStatus('আপনার ব্রাউজারে ভয়েস রিকগনিশন সুবিধা নেই। অনুগ্রহ করে Chrome বা Edge ব্যবহার করুন।', 'error');
      return;
    }

    stopSpeaking();
    openModal();

    try {
      recognition.start();
    } catch (e) {
      console.warn('Recognition start exception:', e);
      try {
        recognition.stop();
        setTimeout(() => recognition.start(), 200);
      } catch (err) {}
    }
  }

  function stopListening() {
    if (recognition && isListening) {
      try {
        recognition.stop();
      } catch (e) {}
    }
    isListening = false;
    setListeningState(false);
  }

  // Browser Text-To-Speech (SpeechSynthesis in bn-BD)
  function speakReply(text) {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'bn-BD';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const bnVoice = voices.find(v => v.lang === 'bn-BD' || v.lang.startsWith('bn'));
    if (bnVoice) {
      utterance.voice = bnVoice;
    }

    utterance.onstart = function () {
      if (speakingIcon) speakingIcon.classList.add('text-amber-600', 'animate-bounce');
    };

    utterance.onend = utterance.onerror = function () {
      if (speakingIcon) speakingIcon.classList.remove('animate-bounce');
    };

    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  // Handle Recognized User Speech
  function handleRecognizedSpeech(text) {
    if (!text || !text.trim()) return;

    openModal();

    userTranscriptContainer.classList.remove('hidden');
    userTranscript.textContent = text;

    setStatus('খুঁজছি... অনুগ্রহ করে অপেক্ষা করুন...', 'processing');
    console.log('Sending voice query to backend:', text);

    fetch('/api/voice-assistant/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: text })
    })
      .then(response => {
        if (!response.ok) {
          throw new Error('Server responded with HTTP ' + response.status);
        }
        return response.json();
      })
      .then(data => {
        console.log('Voice Assistant API Response:', data);
        const reply = data.reply || 'বুঝতে পারিনি, আবার বলুন।';
        const products = data.products || [];

        if (data.debug_error) {
          console.warn('Backend debug error:', data.debug_error);
        }

        // Display reply bubble
        replyContainer.classList.remove('hidden');
        replyText.textContent = reply;

        // Speak reply via browser TTS
        speakReply(reply);

        // Display products
        renderProducts(products);

        setStatus('সম্পন্ন! নতুন কিছু বলতে মাইকে চাপ দিন।', 'idle');
      })
      .catch(error => {
        console.error('Voice Assistant API Error:', error);
        const fallback = 'বুঝতে পারিনি, আবার বলুন।';
        replyContainer.classList.remove('hidden');
        replyText.textContent = fallback;
        speakReply(fallback);
        renderProducts([]);
        setStatus('সার্ভারে সমস্যা হয়েছে। আবার চেষ্টা করুন।', 'error');
      });
  }

  // Render Product Cards
  function renderProducts(products) {
    productsGrid.innerHTML = '';

    if (!products || products.length === 0) {
      resultsContainer.classList.add('hidden');
      return;
    }

    resultsContainer.classList.remove('hidden');
    resultsCount.textContent = products.length + 'টি পণ্য';

    products.forEach(p => {
      const card = document.createElement('a');
      card.href = p.product_url || '#';
      card.className = 'group flex items-center gap-3 p-2 bg-gray-50 hover:bg-amber-50 rounded-xl border border-gray-200 hover:border-amber-300 transition duration-200';

      const imgContainer = document.createElement('div');
      imgContainer.className = 'w-14 h-14 flex-shrink-0 bg-white rounded-lg overflow-hidden border border-gray-200 flex items-center justify-center';

      if (p.image_url) {
        const img = document.createElement('img');
        img.src = p.image_url;
        img.alt = p.name;
        img.className = 'w-full h-full object-cover group-hover:scale-105 transition duration-200';
        imgContainer.appendChild(img);
      } else {
        imgContainer.innerHTML = '<i class="fa-solid fa-box text-gray-400 text-lg"></i>';
      }

      const infoContainer = document.createElement('div');
      infoContainer.className = 'flex flex-col flex-grow min-w-0';

      const title = document.createElement('h4');
      title.className = 'text-xs font-semibold text-gray-800 truncate group-hover:text-amber-700';
      title.textContent = p.name;

      const subInfo = document.createElement('div');
      subInfo.className = 'flex items-center gap-2 mt-0.5';

      const price = document.createElement('span');
      price.className = 'text-xs font-bold text-amber-600';
      price.textContent = '৳ ' + p.price;

      subInfo.appendChild(price);

      if (p.is_offer) {
        const offerBadge = document.createElement('span');
        offerBadge.className = 'text-[9px] px-1.5 py-0.2 bg-red-100 text-red-600 font-bold rounded';
        offerBadge.textContent = 'Offer';
        subInfo.appendChild(offerBadge);
      }

      if (p.condition) {
        const condBadge = document.createElement('span');
        const isNew = (p.condition || '').toLowerCase() === 'new';
        condBadge.className = isNew
          ? 'text-[9px] px-1.5 py-0.5 bg-green-100 text-green-700 font-semibold rounded'
          : 'text-[9px] px-1.5 py-0.5 bg-blue-100 text-blue-700 font-semibold rounded';
        condBadge.textContent = p.condition;
        subInfo.appendChild(condBadge);
      }

      if (p.avg_rating) {
        const ratingBadge = document.createElement('span');
        ratingBadge.className = 'text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-800 font-bold rounded flex items-center gap-0.5';
        ratingBadge.innerHTML = '<i class="fa-solid fa-star text-amber-500 text-[8px]"></i> ' + p.avg_rating;
        subInfo.appendChild(ratingBadge);
      }

      infoContainer.appendChild(title);
      infoContainer.appendChild(subInfo);

      const actionIcon = document.createElement('div');
      actionIcon.className = 'text-gray-400 group-hover:text-amber-600 pr-1 transition';
      actionIcon.innerHTML = '<i class="fa-solid fa-chevron-right text-xs"></i>';

      card.appendChild(imgContainer);
      card.appendChild(infoContainer);
      card.appendChild(actionIcon);

      productsGrid.appendChild(card);
    });
  }

  // Event Listeners
  triggerBtn.addEventListener('click', function () {
    if (modal.classList.contains('hidden')) {
      startListening();
    } else {
      if (isListening) {
        stopListening();
      } else {
        startListening();
      }
    }
  });

  modalCloseBtn.addEventListener('click', closeModal);
  retryBtn.addEventListener('click', startListening);

  const instantSearchBtn = document.getElementById('voice-instant-search-btn');
  if (instantSearchBtn) {
    instantSearchBtn.addEventListener('click', function () {
      if (lastCapturedText) {
        stopListening();
        hasHandledFinalSpeech = true;
        handleRecognizedSpeech(lastCapturedText);
      }
    });
  }

  // Example Prompt Chips
  chips.forEach(chip => {
    chip.addEventListener('click', function () {
      const text = this.textContent.trim();
      handleRecognizedSpeech(text);
    });
  });

  // Pre-load voices on voice changes
  if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = function () {
      window.speechSynthesis.getVoices();
    };
  }
});
