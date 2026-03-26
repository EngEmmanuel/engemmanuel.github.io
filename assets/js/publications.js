(function() {
	var listElement = document.getElementById('publications-list');
	if (!listElement) return;

	var updatedElement = document.getElementById('publications-updated');

	function clearElement(el) {
		while (el.firstChild) {
			el.removeChild(el.firstChild);
		}
	}

	function setMessage(message) {
		clearElement(listElement);
		var item = document.createElement('li');
		item.textContent = message;
		listElement.appendChild(item);
	}

	function formatPublication(pub) {
		var parts = [];
		if (pub.venue) parts.push(pub.venue);
		return parts.join(' — ');
	}

	function appendAuthorsWithBoldName(container, authors) {
		var targetNames = ['Emmanuel Oladokun', 'E Oladokun'];
		if (!authors) {
			container.appendChild(document.createTextNode(''));
			return;
		}

		var targetName = null;
		for (var t = 0; t < targetNames.length; t++) {
			if (authors.indexOf(targetNames[t]) !== -1) {
				targetName = targetNames[t];
				break;
			}
		}

		if (!targetName) {
			container.appendChild(document.createTextNode(authors));
			return;
		}

		var remaining = authors;
		while (remaining.length > 0) {
			var matchIndex = remaining.indexOf(targetName);
			if (matchIndex === -1) {
				container.appendChild(document.createTextNode(remaining));
				break;
			}

			if (matchIndex > 0) {
				container.appendChild(document.createTextNode(remaining.slice(0, matchIndex)));
			}

			var strong = document.createElement('strong');
			strong.textContent = targetName;
			container.appendChild(strong);

			remaining = remaining.slice(matchIndex + targetName.length);
		}
	}

	function collaboratorForPublication(pub) {
		var title = (pub && pub.title ? pub.title : '').toLowerCase();
		if (title.indexOf('linear solver tolerance') !== -1 || title.indexOf('ecmor') !== -1) {
			return 'SLB';
		}
		return 'GE HealthCare';
	}

	// Papers with publicly available code — keyed by lowercase title fragment.
	var PUBLIC_REPOS = {
		'echolvm': 'https://github.com/EngEmmanuel/EchoLVFM',
	};

	function publicRepoForPublication(pub) {
		var title = (pub && pub.title ? pub.title : '').toLowerCase();
		for (var key in PUBLIC_REPOS) {
			if (title.indexOf(key) !== -1) {
				return PUBLIC_REPOS[key];
			}
		}
		return null;
	}

	function buildArxivSearchUrl(title) {
		var query = encodeURIComponent(title || '');
		return 'https://arxiv.org/search/?query=' + query + '&searchtype=title';
	}

	function isBestPaperPublication(pub) {
		var title = (pub && pub.title ? pub.title : '').toLowerCase();
		return title.indexOf('cross-modality generation using lora diffusion') !== -1;
	}

	function triggerLocalConfetti(target) {
		if (!target || target.classList.contains('confetti-active')) return;
		target.classList.add('confetti-active');

		var colors = ['#8ebebc', '#9ececc', '#e27689', '#f5fafa'];
		for (var i = 0; i < 18; i += 1) {
			var piece = document.createElement('span');
			piece.className = 'confetti-piece';
			piece.style.setProperty('--dx', (Math.random() * 90 - 45).toFixed(1) + 'px');
			piece.style.setProperty('--dy', (-30 - Math.random() * 45).toFixed(1) + 'px');
			piece.style.setProperty('--rotation', (Math.random() * 360).toFixed(1) + 'deg');
			piece.style.backgroundColor = colors[i % colors.length];
			target.appendChild(piece);

			setTimeout((function(el) {
				return function() {
					if (el && el.parentNode) {
						el.parentNode.removeChild(el);
					}
				};
			})(piece), 700);
		}

		setTimeout(function() {
			target.classList.remove('confetti-active');
		}, 750);
	}

	function appendBestPaperBadge(container, pub) {
		if (!isBestPaperPublication(pub)) return;

		container.appendChild(document.createTextNode(' '));
		var badge = document.createElement('span');
		badge.className = 'publication-badge best-paper-badge';
		badge.textContent = 'Best Paper (ASMUS-MICCAI 2025)';
		badge.title = 'Hover for celebration';
		badge.addEventListener('mouseenter', function() {
			triggerLocalConfetti(badge);
		});
		container.appendChild(badge);
	}

	function appendResourcesLine(container, pub) {
		var resources = document.createElement('div');
		resources.className = 'publication-resources';

		var githubIcon = document.createElement('span');
		githubIcon.className = 'icon brands fa-github';
		var githubLabel = document.createElement('span');
		githubLabel.className = 'label';
		githubLabel.textContent = 'GitHub';
		githubIcon.appendChild(githubLabel);
		resources.appendChild(githubIcon);

		var repoUrl = publicRepoForPublication(pub);
		if (repoUrl) {
			resources.appendChild(document.createTextNode(' '));
			var repoLink = document.createElement('a');
			repoLink.href = repoUrl;
			repoLink.target = '_blank';
			repoLink.rel = 'noopener noreferrer';
			repoLink.textContent = 'Code available';
			resources.appendChild(repoLink);
		} else {
			var collaborator = collaboratorForPublication(pub);
			resources.appendChild(document.createTextNode(' Proprietary (' + collaborator + ' collaboration; not all materials can be shared)'));
		}

		resources.appendChild(document.createTextNode(' | '));

		var arxivLink = document.createElement('a');
		arxivLink.className = 'publication-arxiv-link';
		arxivLink.href = buildArxivSearchUrl(pub && pub.title ? pub.title : '');
		arxivLink.target = '_blank';
		arxivLink.rel = 'noopener noreferrer';

		var arxivIcon = document.createElement('img');
		arxivIcon.src = 'assets/css/images/arxiv.svg';
		arxivIcon.alt = 'arXiv';
		arxivIcon.className = 'publication-arxiv-logo';
		arxivLink.appendChild(arxivIcon);
		arxivLink.appendChild(document.createTextNode(' arXiv'));

		resources.appendChild(arxivLink);
		container.appendChild(resources);
	}

	function renderPublications(data) {
		if (!data || !Array.isArray(data.publications) || data.publications.length === 0) {
			setMessage('Publications will appear here shortly.');
			return;
		}

		clearElement(listElement);
		data.publications.forEach(function(pub) {
			var item = document.createElement('li');
			var titleStrong = document.createElement('strong');

			if (pub.url) {
				var link = document.createElement('a');
				link.href = pub.url;
				link.target = '_blank';
				link.rel = 'noopener noreferrer';
				link.textContent = pub.title || 'Untitled publication';
				titleStrong.appendChild(link);
			} else {
				titleStrong.textContent = pub.title || 'Untitled publication';
			}

			item.appendChild(titleStrong);
			appendBestPaperBadge(item, pub);

			if (pub.authors) {
				item.appendChild(document.createTextNode(' — '));
				appendAuthorsWithBoldName(item, pub.authors);
			}

			var details = formatPublication(pub);
			if (details) {
				item.appendChild(document.createTextNode(' — ' + details));
			}

			appendResourcesLine(item, pub);

			listElement.appendChild(item);
		});

		if (updatedElement && data.updated_at) {
			var updatedDate = new Date(data.updated_at);
			if (!Number.isNaN(updatedDate.getTime())) {
				updatedElement.textContent = 'Last updated: ' + updatedDate.toLocaleDateString();
			}
		}
	}

	fetch('publications.json')
		.then(function(response) {
			if (!response.ok) {
				throw new Error('Failed to load publications.');
			}
			return response.json();
		})
		.then(renderPublications)
		.catch(function() {
			setMessage('Unable to load publications right now.');
		});
})();
