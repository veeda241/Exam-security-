// Filters Component - Filter Controls
export class FilterControls {
    constructor(onFilterChange) {
        this.onFilterChange = onFilterChange;
        this.searchTerm = '';
        this.statusFilter = 'all';
    }

    init() {
        const searchInput = document.getElementById('searchInput');
        const statusSelect = document.getElementById('statusFilter');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value;
                this.emitChange();
            });
        }

        if (statusSelect) {
            statusSelect.addEventListener('change', (e) => {
                this.statusFilter = e.target.value;
                this.emitChange();
            });
        }
    }

    emitChange() {
        if (this.onFilterChange) {
            this.onFilterChange({
                search: this.searchTerm,
                status: this.statusFilter
            });
        }
    }

    reset() {
        this.searchTerm = '';
        this.statusFilter = 'all';

        const searchInput = document.getElementById('searchInput');
        const statusSelect = document.getElementById('statusFilter');

        if (searchInput) searchInput.value = '';
        if (statusSelect) statusSelect.value = 'all';

        this.emitChange();
    }

    getFilters() {
        return {
            search: this.searchTerm,
            status: this.statusFilter
        };
    }
}
