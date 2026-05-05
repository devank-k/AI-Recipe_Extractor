// Recipe Extractor & Meal Planner — Application Logic

const API_BASE = '/api/recipes';

//  State 
let selectedRecipeIds = new Set();

//  DOM Ready 
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    // Allow Enter key to trigger extraction
    document.getElementById('urlInput').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleExtract();
    });
});

// --- Tab Navigation ---

function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    const indicator = document.getElementById('tabIndicator');
    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            tabs.forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
            document.getElementById(tab === 'extract' ? 'extractPanel' : 'historyPanel').classList.add('active');
            indicator.classList.toggle('right', tab === 'history');
            if (tab === 'history') loadHistory();
        });
    });
}

// --- Tab 1: Extract Recipe ---

async function handleExtract() {
    const input = document.getElementById('urlInput');
    const url = input.value.trim();
    if (!url) { showToast('Please enter a recipe URL.', 'error'); return; }

    // Basic URL validation
    try { new URL(url); } catch { showToast('Please enter a valid URL.', 'error'); return; }

    showLoading('Extracting recipe...', 'Scraping page & analyzing with AI — this may take 15-30 seconds');
    try {
        const res = await fetch(`${API_BASE}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await res.json();
        hideLoading();
        console.log('Got extraction data:', data); // debug
        if (!res.ok) {
            showToast(data.detail || 'Extraction failed.', 'error');
            return;
        }
        renderRecipe(data, document.getElementById('recipeDisplay'));
        showToast(`Recipe extracted: ${data.title}`, 'success');
    } catch (err) {
        hideLoading();
        showToast('Network error — is the backend running?', 'error');
        console.error(err);
    }
}

// --- Tab 2: History ---

async function loadHistory() {
    const tbody = document.getElementById('historyBody');
    const empty = document.getElementById('emptyState');
    try {
        const res = await fetch(API_BASE);
        const recipes = await res.json();
        if (!recipes.length) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';
        tbody.innerHTML = recipes.map(r => `
            <tr>
                <td class="col-check"><input type="checkbox" data-id="${r.id}" onchange="updateSelection()" ${selectedRecipeIds.has(r.id) ? 'checked' : ''}></td>
                <td style="font-weight:600;color:var(--text-primary)">${esc(r.title)}</td>
                <td>${r.cuisine ? `<span class="cuisine-badge" style="font-size:0.7rem;padding:0.2rem 0.6rem">${esc(r.cuisine)}</span>` : '—'}</td>
                <td>${r.difficulty ? difficultyBadge(r.difficulty) : '—'}</td>
                <td style="font-size:0.8rem">${new Date(r.created_at).toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' })}</td>
                <td><button class="btn-details" onclick="showDetails(${r.id})">Details</button></td>
            </tr>
        `).join('');
    } catch (err) {
        showToast('Failed to load history.', 'error');
        console.error(err);
    }
}

async function showDetails(id) {
    showLoading('Loading recipe...');
    try {
        const res = await fetch(`${API_BASE}/${id}`);
        const data = await res.json();
        hideLoading();
        if (!res.ok) { showToast(data.detail || 'Not found.', 'error'); return; }
        renderRecipe(data, document.getElementById('modalBody'));
        document.getElementById('modalOverlay').classList.add('active');
    } catch (err) {
        hideLoading();
        showToast('Failed to load recipe.', 'error');
    }
}

function closeModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('modalOverlay').classList.remove('active');
}

// --- Meal Planner ---

function updateSelection() {
    selectedRecipeIds.clear();
    document.querySelectorAll('#historyBody input[type="checkbox"]:checked').forEach(cb => {
        selectedRecipeIds.add(parseInt(cb.dataset.id));
    });
    const count = selectedRecipeIds.size;
    document.getElementById('selectedCount').textContent = `${count} selected`;
    document.getElementById('mealPlanBtn').disabled = count < 2 || count > 5;
}

function toggleSelectAll(el) {
    document.querySelectorAll('#historyBody input[type="checkbox"]').forEach(cb => { cb.checked = el.checked; });
    updateSelection();
}

async function handleMealPlan() {
    if (selectedRecipeIds.size < 2) { showToast('Select at least 2 recipes.', 'error'); return; }
    showLoading('Generating meal plan...');
    try {
        const res = await fetch(`${API_BASE}/meal-plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipe_ids: Array.from(selectedRecipeIds) }),
        });
        const data = await res.json();
        hideLoading();
        if (!res.ok) { showToast(data.detail || 'Failed.', 'error'); return; }
        renderMealPlan(data);
    } catch (err) {
        hideLoading();
        showToast('Network error.', 'error');
    }
}

function renderMealPlan(data) {
    const body = document.getElementById('mealPlanBody');
    body.innerHTML = `
        <div class="meal-plan-header">
            <h2>🗓️ Your Meal Plan</h2>
            <p style="color:var(--text-secondary)">Combined shopping list for ${data.recipes.length} recipes</p>
        </div>
        <div class="meal-plan-recipes">
            ${data.recipes.map(r => `<span class="mp-recipe-chip">${esc(r.title)}</span>`).join('')}
        </div>
        <div class="section-card glass-card" style="margin-bottom:1rem">
            <h3><span class="emoji">📊</span> Total Nutrition (per serving each)</h3>
            <div class="nutrition-grid">
                <div class="nutrition-item"><div class="nutrition-value">${data.total_nutrition.calories}</div><div class="nutrition-label">Calories</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${data.total_nutrition.protein}</div><div class="nutrition-label">Protein</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${data.total_nutrition.carbs}</div><div class="nutrition-label">Carbs</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${data.total_nutrition.fat}</div><div class="nutrition-label">Fat</div></div>
            </div>
        </div>
        <div class="section-card glass-card">
            <h3><span class="emoji">🛒</span> Merged Shopping List</h3>
            <div class="shopping-categories">
                ${Object.entries(data.merged_shopping_list).map(([cat, items]) => `
                    <div class="shop-category">
                        <h4>${esc(cat)}</h4>
                        <ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    document.getElementById('mealPlanModal').classList.add('active');
}

function closeMealPlanModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('mealPlanModal').classList.remove('active');
}

// --- Recipe Rendering ---

function renderRecipe(r, container) {
    const n = r.nutrition_estimate || {};
    container.innerHTML = `
        <!-- Hero -->
        <div class="recipe-hero card-enter">
            ${r.cuisine ? `<span class="cuisine-badge">${esc(r.cuisine)}</span>` : ''}
            <h2>${esc(r.title)}</h2>
            ${r.difficulty ? difficultyBadge(r.difficulty) : ''}
            <div class="recipe-meta">
                ${r.prep_time ? metaChip('Prep', r.prep_time) : ''}
                ${r.cook_time ? metaChip('Cook', r.cook_time) : ''}
                ${r.total_time ? metaChip('Total', r.total_time) : ''}
                ${r.servings ? metaChip('Servings', r.servings) : ''}
            </div>
        </div>

        <!-- Ingredients -->
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">🥘</span> Ingredients</h3>
            <div class="ingredients-grid">
                ${(r.ingredients || []).map(i => `
                    <div class="ingredient-item">
                        <span class="ingredient-qty">${esc(i.quantity)}${i.unit ? ' ' + esc(i.unit) : ''}</span>
                        <span class="ingredient-name">${esc(i.item)}</span>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- Instructions -->
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">📝</span> Instructions</h3>
            <div class="instructions-list">
                ${(r.instructions || []).map((s, i) => `
                    <div class="instruction-step">
                        <div class="step-num">${i + 1}</div>
                        <div class="step-text">${esc(s)}</div>
                    </div>
                `).join('')}
            </div>
        </div>

        <!-- Nutrition -->
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">📊</span> Nutrition Estimate <span style="font-weight:400;color:var(--text-muted);font-size:0.8rem">(per serving)</span></h3>
            <div class="nutrition-grid">
                <div class="nutrition-item"><div class="nutrition-value">${n.calories || '—'}</div><div class="nutrition-label">Calories</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${n.protein || '—'}</div><div class="nutrition-label">Protein</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${n.carbs || '—'}</div><div class="nutrition-label">Carbs</div></div>
                <div class="nutrition-item"><div class="nutrition-value">${n.fat || '—'}</div><div class="nutrition-label">Fat</div></div>
            </div>
        </div>

        <!-- Substitutions -->
        ${(r.substitutions && r.substitutions.length) ? `
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">🔄</span> Ingredient Substitutions</h3>
            <div class="substitution-list">
                ${r.substitutions.map(s => `<div class="substitution-item">${esc(s)}</div>`).join('')}
            </div>
        </div>` : ''}

        <!-- Shopping List -->
        ${(r.shopping_list && Object.keys(r.shopping_list).length) ? `
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">🛒</span> Shopping List</h3>
            <div class="shopping-categories">
                ${Object.entries(r.shopping_list).map(([cat, items]) => `
                    <div class="shop-category">
                        <h4>${esc(cat)}</h4>
                        <ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>
                    </div>
                `).join('')}
            </div>
        </div>` : ''}

        <!-- Related Recipes -->
        ${(r.related_recipes && r.related_recipes.length) ? `
        <div class="section-card glass-card card-enter">
            <h3><span class="emoji">🍽️</span> Related Recipes</h3>
            <div class="related-grid">
                ${r.related_recipes.map(name => `<div class="related-item">${esc(name)}</div>`).join('')}
            </div>
        </div>` : ''}
    `;
}

// --- Utilities ---

function metaChip(label, value) {
    return `<span class="meta-chip"><span class="meta-label">${label}</span> ${esc(String(value))}</span>`;
}

function difficultyBadge(level) {
    const l = (level || '').toLowerCase();
    return `<span class="difficulty-badge difficulty-${l}">${l}</span>`;
}

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function showLoading(text, sub) {
    document.getElementById('loadingText').textContent = text || 'Loading...';
    const subEl = document.querySelector('.loading-sub');
    if (subEl) subEl.textContent = sub || '';
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fadeout');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
