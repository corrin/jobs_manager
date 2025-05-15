import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"



document.addEventListener('DOMContentLoaded', () => {
    try {
        const dataService = new CalendarDataService('/api/reports/calendar');
        const formatter = new EventFormatter(dataService);
        const view = new CalendarView('calendar', 'calendarLoader', formatter);

        const controller = new CalendarController(
            dataService,
            view,
            formatter
        );

        if (!controller.initialize()) {
            alert('Error during calendar initialization. Check console for more details.');
        }
    } catch (error) {
        console.error('Fatal error initializing KPI calendar reports:', error);
        alert('A serious error ocurred when initializing this page: ' + error.message);
    }
});

class CalendarView {

    /**
     * 
     * @param {String} calendarElementId 
     * @param {String} loaderElementId 
     */
    constructor(calendarElementId, loaderElementId, formatter) {
        this.calendarEl = document.getElementById(calendarElementId);
        this.loaderEl = document.getElementById(loaderElementId);
        this.formatter = formatter;
        this.calendar = null;
        this.gpChart = null;

        if (!this.calendarEl) {
            throw new Error(`Calendar element with id ${this.calendar} not found`);
        }
    }

    /**
     * Initializes the FullCalendar object based on the calendar member element
     * @param {Function} datesSetCallback The function that'll be executed after the dates are set
     * @returns {Calendar} The FullCalendar object
     */
    initializeCalendar(datesSetCallback) {
        this.calendar = new FullCalendar.Calendar(this.calendarEl, {
            initialView: 'dayGridMonth',
            firstDay: 1,
            hiddenDays: [0, 6],
            showNonCurrentDates: false,
            height: 'auto',
            timeZone: 'Pacific/Auckland',
            headerToolbar: {
                left: 'prev,next',
                center: 'title',
                right: ''
            },
            datesSet: datesSetCallback,
            eventContent: (arg) => this.#createEventContent(arg),
            eventDidMount: (info) => this.setupEventTooltip(info)
        });

        this.calendar.render();
        return this.calendar;
    }

    /**
     * Displays the loader element while hides the calendar
     */
    showLoader() {
        if (this.loaderEl) this.loaderEl.style.display = 'flex';
        if (this.calendarEl) this.calendarEl.style.display = 'none';
    }

    /**
     * Hides the loader element while displays the calendar
     */
    hideLoader() {
        if (this.loaderEl) this.loaderEl.style.display = 'none';
        if (this.calendarEl) this.calendarEl.style.display = 'block';
        this.updateSize();
    }

    /**
     * Calls the FullCalendar instance function that updates its size
     */
    updateSize() {
        if (this.calendar) this.calendar.updateSize();
    }

    /**
     * Updates the summary cards of the page based on the monthlyTotals and thresholds received from the API
     * @param {Object} monthlyTotals 
     * @param {Object} thresholds 
     */
    updateSummaryCards(monthlyTotals, thresholds) {
        const billableHours = monthlyTotals.billable_hours != null
            ? this.formatter.formatNumber(monthlyTotals.billable_hours, 1)
            : '0.0';
        const billablePercentage = monthlyTotals.billable_percentage != null
            ? this.formatter.formatNumber(monthlyTotals.billable_percentage, 1)
            : '0.0';
        const grossProfit = monthlyTotals.gross_profit != null
            ? this.formatter.formatCurrency(monthlyTotals.gross_profit)
            : '$0.00';
        const avgDailyGP = monthlyTotals.avg_daily_gp != null
            ? this.formatter.formatNumber(monthlyTotals.avg_daily_gp, 2)
            : '0.00';
        const shopPercentage = monthlyTotals.shop_percentage != null
            ? this.formatter.formatNumber(monthlyTotals.shop_percentage, 1)
            : '0.0';

        document.getElementById('totalBillableHours').textContent = billableHours;
        document.getElementById('billablePercentage').textContent = billablePercentage;
        document.getElementById('totalGrossProfit').textContent = grossProfit;
        document.getElementById('avgDailyGPSoFar').textContent = avgDailyGP;
        document.getElementById('shopPercentage').textContent = shopPercentage;

        const shopTarget = thresholds && thresholds.shop_hours_target != null
            ? this.formatter.formatNumber(thresholds.shop_hours_target, 1)
            : '0.0';
        document.getElementById('shopTarget').textContent = shopTarget;

        document.getElementById('greenDays').textContent = monthlyTotals.days_green || 0;
        document.getElementById('amberDays').textContent = monthlyTotals.days_amber || 0;
        document.getElementById('redDays').textContent = monthlyTotals.days_red || 0;
        document.getElementById('workingDays').textContent = monthlyTotals.working_days || 0;

        const billableColorClass = monthlyTotals.color_hours || 'neutral';
        const gpColorClass = monthlyTotals.color_gp || 'neutral';
        const shopColorClass = monthlyTotals.color_shop || 'neutral';

        const billableHoursCard = document.getElementById('billableHoursCard');
        billableHoursCard.className =
            billableHoursCard.className.replace(/card-status-\w+/g, '') + ` card-status-${billableColorClass}`;

        const gpCard = document.getElementById("grossProfitCard");
        gpCard.className =
            gpCard.className.replace(/card-status-\w+/g, '') + ` card-status-${gpColorClass}`;
            
        // Add shop card coloring
        const shopCard = document.getElementById("shopJobsCard");
        if (shopCard) {
            shopCard.className = 
                shopCard.className.replace(/card-status-\w+/g, '') + ` card-status-${shopColorClass}`;
        }

        const avgBillableHoursSoFar = monthlyTotals.avg_billable_hours_so_far != null
            ? this.formatter.formatNumber(monthlyTotals.avg_billable_hours_so_far, 1)
            : '0.0';
        const avgDailyGpSoFar = monthlyTotals.avg_daily_gp_so_far != null
            ? this.formatter.formatCurrency(monthlyTotals.avg_daily_gp_so_far)
            : '$0.00';

        document.getElementById('elapsedWorkdays').textContent = monthlyTotals.elapsed_workdays || 0;
        document.getElementById('remainingWorkdays').textContent = monthlyTotals.remaining_workdays || 0;

        document.getElementById('avgBillableHoursSoFar').textContent = avgBillableHoursSoFar;
        document.getElementById('avgDailyGPSoFar').textContent = avgDailyGpSoFar;
    }

    /**
     * Updates the captions based on the thresholds received from the API.
     * @param {Array<Object>} thresholds 
     * @returns {void}
     */
    updateCaptions(thresholds) {
        if (!thresholds) return;

        const greenThreshold = thresholds.billable_threshold_green || 45;
        const amberThreshold = thresholds.billable_threshold_amber || 30;

        document.getElementById('captionGreen').textContent = `≥ ${greenThreshold}`;
        document.getElementById('captionAmberMin').textContent = amberThreshold;
        document.getElementById('captionAmberMax').textContent = this.formatter.formatNumber(greenThreshold - 0.01, 1);
        document.getElementById('captionRed').textContent = amberThreshold;
    }

    /**
     * Creates custom HTML content for calendar events based on event properties
     * 
     * In more detail, generates the visual representation of each day's data in the 
     * calendar. It formats numeric values, applies appropriate styling based on status colors,
     * and structures the information in a card layout with sections for billable hours,
     * gross profit, and detailed metrics.
     * 
     * @private
     * @param {Object} arg - The event argument from FullCalendar's eventContent callback
     * @returns {Object|null} HTML content for the event or null if it's a background event
     */
    #createEventContent(arg) {
        if (arg.event.display === 'background') {
            return null; // Skip content for background events
        }

        const props = arg.event.extendedProps;
        if (!props) {
            return null;
        }

        if (props.holiday) {
            return {
                html: `<div class="event-content event-card-holiday">
                        <div class="holiday-indicator"></div>
                        <div class="event-title holiday-title">${props.holiday_name || 'Holiday'}</div>
                       </div>`
            };
        }

        // Round values for cleaner display
        const billable = props.billable_hours != null
            ? parseFloat(props.billable_hours).toFixed(1)
            : '0.0';
        const totalHours = props.total_hours != null
            ? parseFloat(props.total_hours).toFixed(1)
            : '0.0';
        const shopHours = props.shop_hours != null
            ? parseFloat(props.shop_hours).toFixed(1)
            : '0.0';
        const shopPercentage = props.shop_percentage != null
            ? parseFloat(props.shop_percentage).toFixed(0)
            : '0';
        const gp = props.gross_profit != null
            ? this.formatter.formatCurrency(props.gross_profit)
            : '$0.00';

        // Determine class based on status
        const colorClass = props.color ? `event-card-${props.color}` : '';

        const isFutureDate = arg.event.extendedProps.isFutureDate;
        const futureClass = isFutureDate ? 'future-date' : '';

        // Create HTML with tooltip data directly in the card
        return {
            html: `<div class="event-content ${colorClass} ${futureClass}">
                    <div class="status-indicator status-indicator-${props.color || 'green'}"></div>
                    <div class="event-title">${billable}h</div>
                    <div class="event-gp">${gp}</div>
                    <div class="event-details">
                        <div class="event-detail-item">
                            <span class="event-detail-value">${totalHours}h</span>
                            <span class="event-detail-label">Total</span>
                        </div>
                        <div class="event-detail-item">
                            <span class="event-detail-value">${shopHours}h</span>
                            <span class="event-detail-label">Shop</span>
                        </div>
                        <div class="event-detail-item">
                            <span class="event-detail-value">${shopPercentage}%</span>
                            <span class="event-detail-label">Shop%</span>
                        </div>
                        ${isFutureDate ? '<div class="future-indicator">Not elapsed yet</div>' : ''}
                    </div>
                  </div>`
        };
    }

    /**
     * Shows the day details modal with KPI information for the selected day
     * Displays revenue, costs, and profit breakdown in tables and visualizations
     * 
     * @param {Object} dayData - The data for the selected day containing all KPI metrics
     * @private
     */
    #showDayDetailsModal(dayData) {
        console.group(`KPI Details for ${dayData.date}`);
        console.log('Full day data:', dayData);

        if (dayData.details) {
            console.log('Revenue breakdown:', {
                'Time Revenue': dayData.details.time_revenue,
                'Material Revenue': dayData.details.material_revenue,
                'Adjustment Revenue': dayData.details.adjustment_revenue,
                'Total Revenue': dayData.details.total_revenue
            });
            console.log('Cost breakdown:', {
                'Staff Cost': dayData.details.staff_cost,
                'Material Cost': dayData.details.material_cost,
                'Adjustment Cost': dayData.details.adjustment_cost,
                'Total Cost': dayData.details.total_cost
            });
            console.log('Profit breakdown:', dayData.details.profit_breakdown);
        }
        console.groupEnd();

        if (!dayData.details) return;

        const updateElement = (id, value, formatter = (val) => this.formatter.formatCurrency(val)) => {
            const element = document.getElementById(id);
            if (element) element.textContent = formatter(value);
        };

        const items = {
            revenue: ['time_revenue', 'material_revenue', 'adjustment_revenue', 'total_revenue'],
            cost: ['staff_cost', 'material_cost', 'adjustment_cost', 'total_cost']
        };

        // Iterate through both categories
        ['revenue', 'cost'].forEach(category => {
            items[category].forEach(item => {
                const elementId = `modal-${item.replace('_', '-')}`;
                const value = dayData.details[item];
                updateElement(elementId, value);
            });
        });

        const breakdowns = ['labor', 'material', 'adjustment'];

        let totalProfit = 0;
        breakdowns.forEach(bk => {
            const profit = dayData.details.profit_breakdown?.[`${bk}_profit`] ?? 0;
            totalProfit += profit;
            updateElement(`modal-${bk}-profit`, profit);
        });

        updateElement('modal-gross-profit', totalProfit);

        if (totalProfit === 0) {
            renderMessages([{ 
                "level": "warning", 
                "message": "No data found for that day. Unable to display modal" 
            }], 'toast-container', false);
            return;
        }

        // Create the donut chart to visualize profit breakdown
        this.#createProfitDonutChart(dayData, totalProfit);

        const formattedDate = new Intl.DateTimeFormat("en-NZ", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
            timeZone: "Pacific/Auckland"
        }).format(new Date(dayData.date));

        document.getElementById('dayDetailsModalLabel').textContent = `Details for ${formattedDate}`;

        const modal = new bootstrap.Modal(document.getElementById('dayDetailsModal'));
        modal.show();
    }

    /**
     * Creates a donut chart to visualize profit breakdown by category
     * 
     * @param {Object} dayData - The data for the selected day containing profit breakdown
     * @param {number} totalProfit - The total profit value for the day
     * @private
     */
    #createProfitDonutChart(dayData, totalProfit) {
        if (this.gpChart) {
            this.gpChart.destroy();
        }
        
        let ctx = document.getElementById("gpDonutChart");
        if (!ctx) {
            const container = document.querySelector('.profit-breakdown-container');
            if (container) {
                container.innerHTML = `
                    <div class="text-center" style="max-width: 400px; margin: 0 auto;">
                        <div style="width: 70px; height: 70px; margin: 0 auto;">
                            <canvas id="gpDonutChart"></canvas>
                        </div>
                        <div class="d-flex justify-content-center flex-wrap mt-3">
                            <ul id="gpLegend" class="list-inline mb-0 text-center"></ul>
                        </div>
                    </div>
                `;
                ctx = document.getElementById("gpDonutChart");
            } else {
                console.error('Profit breakdown container not found');
                return;
            }
        }

        const segments = [
            { label: "Labor",      value: dayData.details.profit_breakdown.labor_profit,      color: "#3b82f6" },
            { label: "Material",   value: dayData.details.profit_breakdown.material_profit,   color: "#22c55e" },
            { label: "Adjustments", value: dayData.details.profit_breakdown.adjustment_profit, color: "#06b6d4" }
        ];

        const data = segments.filter(s => Math.abs(s.value) > 0.01);

        this.gpChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(s => s.label),
                datasets: [{
                    data: data.map(s => Math.abs(s.value)),
                    backgroundColor: data.map(s => s.color),
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                const segment = segments.find(s => s.label === ctx.label);
                                const multiplier = segment && segment.value < 0 ? -1 : 1;
                                return `${ctx.label}: ${this.formatter.formatCurrency(ctx.raw * multiplier)}`;
                            }
                        }
                    },
                },
                cutout: "65%",
            },
            plugins: [{
                id: "centerText",
                afterDraw: (chart, _, opts) => {
                    const {ctx, chartArea: {width, height}} = chart;
                    ctx.save();
                    ctx.font = "600 0.65rem 'Inter', sans-serif";
                    ctx.fillStyle = "#111";
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    ctx.fillText(
                        this.formatter.formatCurrency(totalProfit),
                        chart.getDatasetMeta(0).data[0]?.x || width/2,
                        chart.getDatasetMeta(0).data[0]?.y || height/2
                    );
                    ctx.restore();
                }
            }]
        });

        const gpLegend = document.getElementById("gpLegend");
        gpLegend.className = "list-inline mb-0 text-center w-100";
        gpLegend.innerHTML = data.map(({label, color, value}) => `
            <li class="list-inline-item mx-1 mb-1">
                <div class="d-inline-flex align-items-center">
                    <span style="display:inline-block;width:10px;height:10px;background:${color};
                                border-radius:3px;margin-right:4px;"></span>
                    ${label} (${this.formatter.formatCurrency(value)})
                </div>
            </li>`).join("");
    }

    /**
     * Sets up tooltips for calendar events with detailed information about hours and profit.
     * 
     * @private
     * @param {Object} info - The event information object provided by FullCalendar
     * @returns {void}
     */
    setupEventTooltip(info) {
        if (info.event.display === 'background') {
            return; // Do nothing for background events
        }

        const props = info.event.extendedProps;
        if (!props) {
            return;
        }

        if (props.holiday) {
            info.el.classList.add('holiday-event');
            info.el.style.cursor = 'default';
            info.el.title = `Holiday: ${props.holiday_name || 'Public Holiday'}`;
            return;
        }

        // Apply color class based on status
        if (props.color) {
            info.el.classList.add(`event-${props.color}`);
        }

        info.el.style.cursor = 'pointer';

        info.el.addEventListener('click', () => {
            this.#showDayDetailsModal(props);
        });

        // Add detailed tooltip
        const billableHours = props.billable_hours != null
            ? parseFloat(props.billable_hours).toFixed(1)
            : '0.0';
        const totalHours = props.total_hours != null
            ? parseFloat(props.total_hours).toFixed(1)
            : '0.0';
        const shopHours = props.shop_hours != null
            ? parseFloat(props.shop_hours).toFixed(1)
            : '0.0';
        const grossProfit = props.gross_profit != null
            ? this.formatter.formatCurrency(props.gross_profit)
            : '$0.00';
        const shopPercentage = props.shop_percentage != null
            ? parseFloat(props.shop_percentage).toFixed(1)
            : '0.0';

        // Detailed tooltip
        info.el.title = `Total: ${totalHours}h | Billable: ${billableHours}h | Shop: ${shopHours}h (${shopPercentage}%) | GP: ${grossProfit}`;
    }
}

class CalendarDataService {

    /**
     * 
     * @param {String} apiBaseUrl 
     */
    constructor(apiBaseUrl = '/api/reports/calendar') {
        this.apiBaseUrl = apiBaseUrl;
    }

    /**
     * Fetches calendar data from the defined API URL and validates the data within it
     * 
     * @param {Number} year Required query parameter for the API call
     * @param {Number} month Required query parameter for the API call
     * @returns {Object} The data validated after the API response
     */
    async fetchCalendarData(year, month) {
        try {
            const response = await fetch(`${this.apiBaseUrl}?year=${year}&month=${month}`);

            if (!response.ok) {
                throw new Error(`API responded with status ${response.status}`);
            }

            let data = await response.json();

            data = this.#validateData(data);

            return data;
        } catch (error) {
            console.error('Error fetching calendar data:', error);
            throw error;
        }
    }

    /**
     * Validates the data received from the back-end, falling back for fallback values or throwing an error if it's in an invalid format
     * 
     * @private
     * @param {Object} data The data received from the back-end before any validations
     * @returns {Object} The data after validations
     */
    #validateData(data) {
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid calendar data format');
        }

        if (!data.calendar_data) {
            console.warn('calendar_data not found in response');
            data.calendar_data = {};
        }

        if (!data.monthly_totals) {
            console.warn("monthly_totals not found in response");
            data.monthly_totals = {
                billable_hours: 0,
                total_hours: 0,
                shop_hours: 0,
                gross_profit: 0,
                days_green: 0,
                days_amber: 0,
                days_red: 0,
                working_days: 0,
                billable_percentage: 0,
                shop_percentage: 0,
                avg_daily_gp: 0
            };
        }

        if (!data.thresholds) {
            throw new Error("Thresholds not found in response");
        }

        return data;
    }

    /**
     * Gets the appropriate RGBA color based on the status received from the back-end
     * 
     * @param {String} status The status to be checked
     * @returns {String} The RGBA color 
     */
    getColorForStatus(status) {
        switch (status) {
            case 'green':
                return 'rgba(54, 177, 67, 0.35)';
            case 'amber':
                return 'rgba(249, 199, 79, 0.35)';
            case 'red':
                return 'rgba(247, 37, 133, 0.35)';
            default:
                return 'transparent';
        }
    }
}

class EventFormatter {

    /**
     * 
     * @param {CalendarDataService} dataService 
     */
    constructor(dataService) {
        this.currencyFormatter = new Intl.NumberFormat('en-NZ', {
            style: 'currency',
            currency: 'NZD'
        });
        this.dataService = dataService;
    }

    /**
     * Creates a list of events on the calendar instance based on the data received from the back-end,
     * after sanitizing it.
     * 
     * @param {Array<Object>} calendarData 
     * @returns {Array<Object>} The events to be created on the calendar
     */
    formatEvents(calendarData) {
        console.group("Calendar Data Processing");
        console.log("Raw calendar data:", calendarData);
        
        const firstHoliday = Object.entries(calendarData || {})
            .find(([_, data]) => data && data.holiday);
        
        if (firstHoliday) {
            console.log("Holiday example:", {
                date: firstHoliday[0],
                name: firstHoliday[1].holiday_name,
                dayOfWeek: new Date(firstHoliday[0]).toLocaleDateString('en-NZ', {weekday: 'long'})
            });
        }
        console.groupEnd();
        
        const events = [];

        for (const [date, dayData] of Object.entries(calendarData || {})) {
            if (!dayData) continue;

            const safeData = this.#sanitizeData(date, dayData);

            events.push(...this.#createEventsForDay(date, safeData));
        }

        return events;
    }

    /**
     * Formats a currency value based on the currencyFormatter member of the class
     * 
     * @param {Number} value 
     * @returns 
     */
    formatCurrency(value) {
        return this.currencyFormatter.format(value || 0);
    }


    /**
     * Formats a given number to a given quantity of decimals, falling back to 1 decimal if not provided.
     * 
     * @param {Number} value 
     * @param {Number} decimals 
     * @returns 
     */
    formatNumber(value, decimals = 1) {
        return (value || 0).toFixed(decimals);
    }

    /**
     * Sanitizes a key-value pair date-dayData received from the back-end for a given day.
     * Formats it to the correct object format providing fallback values in case they're not found in dayData.
     * Cleans the formatted object of any null, undefined or NaN value.
     * 
     * @param {Date | String} date 
     * @param {Object} dayData 
     * @returns {Object} The data after proper formatting and sanitizing.
     */
    #sanitizeData(date, dayData) {
        const safeData = {
            date: date,
            day: Number(date.slice(8, 10)),
            billable_hours: 0,
            total_hours: 0,
            shop_hours: 0,
            shop_percentage: 0,
            gross_profit: 0,
            color: 'transparent',
            ...dayData
        }

        for (const [key, value] of Object.entries(safeData)) {
            if (value === null || value === undefined || (typeof value === 'number' && isNaN(value))) {
                console.warn(`Invalid value for ${key} on date ${date}:`, value);
                safeData[key] = 0;
            }
        }

        return safeData;
    }

    /**
     * Creates an event list to be created inside the calendar based on a given date and its related data.
     * 
     * @param {Date} date 
     * @param {any} data 
     * @returns {Array<Object>} The list of events for the given date
     */
    #createEventsForDay(date, data) {
        const events = [];
        const isFutureDate = new Date(date) > new Date().setHours(0, 0, 0, 0);

        const futureClass = isFutureDate ? 'future-date' : '';

        if (data.holiday) {
            events.push({
                start: date,
                allDay: true,
                display: 'background',
                backgroundColor: '#e9f5f9', // Light blue background
                classNames: ['holiday-background']
            });

            events.push({
                title: data.holiday_name || 'Holiday',
                start: date,
                allDay: true,
                extendedProps: { ...data, isFutureDate },
                classNames: ['calendar-day-event', 'holiday-event', futureClass]
            });

            return events;
        }

        // Add background event to color the cell (with low z-index)
        events.push({
            start: date,
            allDay: true,
            display: 'background',
            backgroundColor: this.dataService.getColorForStatus(data.color),
            classNames: [data.color, futureClass]
        });

        // Add event with data to display (with high z-index)
        events.push({
            title: `${this.formatNumber(data.billable_hours, 1)}h | ${this.formatCurrency(data.gross_profit)}`,
            start: date,
            allDay: true,
            extendedProps: { ...data, isFutureDate },
            classNames: ['calendar-day-event', futureClass]
        });

        return events;
    }
}

class CalendarController {

    /**
     * @param {CalendarDataService} dataService 
     * @param {CalendarView} viewRenderer 
     * @param {EventFormatter} formatter 
     */
    constructor(dataService, viewRenderer, formatter) {
        this.dataService = dataService;
        this.view = viewRenderer;
        this.formatter = formatter;

        this.currentData = null;
        this.calendar = null;

        this.onDatesSet = this.onDatesSet.bind(this);
        this.onResize = this.onResize.bind(this);
    }

    /**
     * Converts a Date (UTC instant) to the "same instance" seemed in NZ, returning a new Date object in the browser's timezone.
     * 
     * @param {Date} date 
     */
    getNZParts(date) {
        const fmt = new Intl.DateTimeFormat('en-CA', {
          timeZone: 'Pacific/Auckland',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        });
        const [y, m, d] = fmt.format(date).split('-').map(Number);
        return { year: y, month: m, day: d };
      }

    /**
     * Initializes the calendar object with the proper view funciton based on the onDatesSet method.
     * Loads the data to the initialized calendar object.
     * 
     * @returns {Boolean} boolean indicating whether the initialization occurred successfully or not
     */
    initialize() {
        try {
            this.calendar = this.view.initializeCalendar(this.onDatesSet);

            this.loadCalendarData(new Date());

            window.addEventListener('resize', this.onResize);

            return true;
        } catch (error) {
            console.error("Error initializing calendar:", error);
            this.view.hideLoader();
            return false;
        }
    }

    /**
     * Loads the calendar data with the proper dataService function based on the current year and month.
     * Displays the loader while doing it, and formats any events received from the back-end.
     * Updates the summary cards and captions with the received data, too.
     * Hides the loader when finished, in both success or error.
     * 
     * @param {Date} date 
     */
    async loadCalendarData(date) {
        const { year, month } = this.getNZParts(date);

        const requestKey = `${year}-${month}`;
        this.pendingRequestKey = requestKey;

        try {
            this.view.showLoader();

            const data = await this.dataService.fetchCalendarData(year, month);

            if (this.pendingRequestKey !== requestKey) return;

            this.currentData = data;

            const events = this.formatter.formatEvents(data.calendar_data);
            this.updateCalendar(events);

            this.view.updateSummaryCards(data.monthly_totals, data.thresholds);
            this.view.updateCaptions(data.thresholds);
        } catch (error) {
            console.error('Error loading calendar data:', error);
            alert('Failed to load calendar data: ' + error.message);
        } finally {
            this.view.hideLoader();
        }
    }

    /**
     * Updates the calendar by removing the existing events, loading the received ones and updating the calendar size.
     * 
     * @param {Array<Object>} events The events to be created within the calendar
     * @returns {void}
     */
    updateCalendar(events) {
        if (!this.calendar) return;

        this.calendar.getEventSources().forEach(src => src.remove());
        this.calendar.addEventSource(events);
        this.view.updateSize();
    }

    /**
     * Based on the dateInfo, loads the calendar data.
     * 
     * @param {Object} dateInfo 
     */
    onDatesSet(dateInfo) {
        const newDate = dateInfo.view.calendar.getDate();
        this.loadCalendarData(newDate);
    }

    /**
     * Updates the size of the calendar based on the proper view function.
     */
    onResize() {
        this.view.updateSize();
    }

    /**
     * Destroys the instance by removing the event listener of the window and the members.
     */
    destroy() {
        window.removeEventListener('resize', this.onResize);

        if (this.calendar) {
            this.calendar.destroy();
            this.calendar = null;
        }

        this.currentData = null;

        this.dataService = null;
        this.view = null;
        this.formatter = null;
    }
}
