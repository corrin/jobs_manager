# Project Documentation: Morris Sheetmetal Works Workflow Management System

## **Project Overview**

Morris Sheetmetal Works is a small jobbing shop specializing in custom metal fabrication for a variety of customer needs, ranging from fencepost covers to manhole covers. The goal of this project is to transition the company from a paper-based workflow to a fully digital system, improving efficiency and enabling better oversight while maintaining or increasing operational speed.

### **Current State**

- **Established Workflow**: Running on paper systems for over 50 years.
    - Jobs tracked on paper sheets.
    - Staff time recorded on paper time cards.
- **Operational Challenges**:
    - Tracking profitability is difficult with the current system.
    - Oversight is limited without digital tools.

### **Motivations for Digitization**

1. **Enhanced Oversight**:
    - Track profitability for each job and staff member.
    - Analyze efficiency and identify problem areas.
2. **Operational Efficiency**:
    - Ensure jobs are delivered on time and correctly.
    - Streamline data entry and minimize errors.
    - Standardize processes to reduce training requirements.
3. **Future Scalability**:
    - Enable features like a CRM, purchase orders, and customer-facing tools.
    - Archive past jobs for easier retrieval and repeatability.

---

## **Desired Functionalities**

### **Core Features**

1. **Job Management**:
    - A simple Kanban-style board for tracking job status.
    - Ability to attach drawings and documents to job records.
    - Print job sheets with all necessary information for workers.
2. **Quoting & Estimation**:
    - Fast generation of quotes while on the phone with customers.
    - Link quotes directly to jobs and invoices.
3. **Time Tracking**:
    - Digitize staff time card entries for real-time tracking.
    - Allocate hours to specific jobs and adjust as needed.
    - Monitor progress against job estimates.
4. **Materials Tracking**:
    - Record materials used per job and include costs in customer invoices.
    - Support markup on materials for profitability.
5. **Billing & Payroll**:
    - Generate invoices upon job completion.
    - Ensure staff hours are accurately recorded for payroll.

### **Operational Safeguards**

- Allow mild warnings for discrepancies (e.g., excessive hours logged) but never block inputs.
- Keep data entry as fast and intuitive as flipping through paper records.

### **Analytics & Oversight**

- Job-level profitability analysis.
- Efficiency tracking for individual staff members.
- Insights into quoting accuracy (e.g., time spent quoting jobs that don't materialize).

---

## **Technical Documentation**

### **Settings Module**

This project uses a **modular settings** approach under the `settings/` directory:

- `base.py` - Base settings shared across environments
- `local.py` - Development settings with debug tools (includes ngrok)
- `production_like.py` - Settings for things like gunicorn, backups, security.

By default, Django loads `settings/__init__.py`, which imports either `local` or `production_like` depending on the environment variable `DJANGO_ENV`:

- **Local development**: `DJANGO_ENV=local` (default)
- **Integration mode**: `DJANGO_ENV=production_like` (requires Redis/Celery)

Note: production_like.py enables Xero/Dropbox integration but requires additional services:
- Redis for caching
- Celery for background tasks
- Stricter security settings

### **Installation and Updates**

- For first-time installation instructions, see [initial_install.md](initial_install.md)
- For updating an existing installation, see [updating.md](updating.md)

---

## **Typical Workflow**

1. **Initial Contact**: Customer describes the problem.
2. **Estimation**:
    - GM, quotes manager or similar describes the job
    - Then they estimate the size of the job.
    - It can either be a simple estimate (time estimate + materials estimate + any adjustments)
    - or more complex with time/materials/adjustments broken out
2. **Quoting**:
    - If the customer wants a formal quote then you copy the estimate to a quote
    - Adjust the quote as appropriate, e.g. adding contingency
    - Customer approves the quote.
3. **Production**:
    - The job sheet is printed and handed to the staff member who will work on the job.
    - Jobs are tracked using a Kanban board.
    - Staff record their daily hours for each job using a paper time card
3. **Time Sheets**:
    - Every day you collect the staff time cards and enter them
    - Check for whether it looks sensible, e.g. total and billable hours
    - Use this opportunity to track progress on each job against the estimate
5. **Materials Management**:
    - Enter materials used on a job directly on the job form (this will change in the future).
6. **Completion & Invoicing**:
    - Jobs are marked as complete.
    - Customers are billed.

---

## **Key Metrics**

1. **Job Metrics**:
    - Backlog size.
    - Estimated vs. actual hours.
    - Profitability (estimated vs. actual).
2. **Staff Metrics**:
    - Hours billed to jobs vs. internal work.
    - Individual profitability.

---

## **Scale of Operations**

- **Staff**:
    - 10 workers and 3 office staff
- **Workload**:
    - ~15 jobs/day (~1 job/person/day).
    - Job durations range from 30 minutes to over 1,000 hours.

---

## **Future Goals**

1. **Improved Searchability**:
    - Quickly find and reuse old jobs, including associated drawings and timesheets.
2. **Customer Interaction**:
    - Centralized client profiles with past jobs, invoices, and communications.
3. **Extended Functionality**:
    - Transition to include extranet capabilities, CRM, and standardized workflows.

---

## **Implementation Notes**

- **Data Model**:
    - The foundation includes jobs, time entries, materials, and staff records.
    - The next milestone is to make the system usable for live operations, starting with job entry and printing functionality.
- **Transition Strategy**:
    - Begin with office staff using the system for quoting and job management.
    - Gradually onboard shop staff as the system becomes more robust.
