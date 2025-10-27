// VibeCortex Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
            mobileMenu.classList.add('mobile-menu-enter');
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (mobileMenu && !mobileMenuButton.contains(event.target) && !mobileMenu.contains(event.target)) {
            mobileMenu.classList.add('hidden');
        }
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Initialize image labeling interface if present
    if (document.getElementById('image-canvas')) {
        initializeImageLabeling();
    }
});

// API helper functions
window.api = {
    get: async function(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    },
    
    post: async function(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }
};

// Image labeling functionality
function initializeImageLabeling() {
    const canvas = document.getElementById('image-canvas');
    const ctx = canvas.getContext('2d');
    let isDrawing = false;
    let currentTool = 'bounding_box';
    let startX, startY;
    let annotations = [];
    let currentCategory = null;
    
    // Set up canvas
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    
    // Label category selection
    document.querySelectorAll('.label-category').forEach(category => {
        category.addEventListener('click', function() {
            document.querySelectorAll('.label-category').forEach(c => c.classList.remove('bg-blue-100'));
            this.classList.add('bg-blue-100');
            currentCategory = {
                id: this.dataset.categoryId,
                name: this.querySelector('span').textContent,
                color: this.dataset.color
            };
        });
    });
    
    // Tool selection
    document.querySelectorAll('.tool-button').forEach(button => {
        button.addEventListener('click', function() {
            document.querySelectorAll('.tool-button').forEach(b => b.classList.remove('bg-blue-600'));
            this.classList.add('bg-blue-600');
            currentTool = this.dataset.tool;
        });
    });
    
    function startDrawing(e) {
        if (!currentCategory) {
            alert('Please select a label category first');
            return;
        }
        
        isDrawing = true;
        const rect = canvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
    }
    
    function draw(e) {
        if (!isDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        // Clear canvas and redraw
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawAnnotations();
        
        // Draw current annotation
        ctx.strokeStyle = currentCategory.color;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        
        if (currentTool === 'bounding_box') {
            ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
        } else if (currentTool === 'polygon') {
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(currentX, currentY);
            ctx.stroke();
        } else if (currentTool === 'point') {
            ctx.beginPath();
            ctx.arc(startX, startY, 5, 0, 2 * Math.PI);
            ctx.fillStyle = currentCategory.color;
            ctx.fill();
        }
    }
    
    function stopDrawing(e) {
        if (!isDrawing) return;
        
        isDrawing = false;
        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;
        
        // Create annotation
        const annotation = {
            id: Date.now(),
            category: currentCategory,
            tool: currentTool,
            coordinates: {
                startX: startX,
                startY: startY,
                endX: endX,
                endY: endY
            }
        };
        
        annotations.push(annotation);
        drawAnnotations();
    }
    
    function drawAnnotations() {
        annotations.forEach(annotation => {
            ctx.strokeStyle = annotation.category.color;
            ctx.fillStyle = annotation.category.color;
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            
            if (annotation.tool === 'bounding_box') {
                ctx.strokeRect(
                    annotation.coordinates.startX,
                    annotation.coordinates.startY,
                    annotation.coordinates.endX - annotation.coordinates.startX,
                    annotation.coordinates.endY - annotation.coordinates.startY
                );
            } else if (annotation.tool === 'polygon') {
                ctx.beginPath();
                ctx.moveTo(annotation.coordinates.startX, annotation.coordinates.startY);
                ctx.lineTo(annotation.coordinates.endX, annotation.coordinates.endY);
                ctx.stroke();
            } else if (annotation.tool === 'point') {
                ctx.beginPath();
                ctx.arc(annotation.coordinates.startX, annotation.coordinates.startY, 5, 0, 2 * Math.PI);
                ctx.fill();
            }
        });
    }
    
    // Save annotations
    document.getElementById('save-annotations')?.addEventListener('click', function() {
        // Save annotations to server
        console.log('Saving annotations:', annotations);
        // TODO: Implement API call to save annotations
    });
}