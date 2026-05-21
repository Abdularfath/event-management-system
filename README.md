# Unified Event Lifecycle Management System (EMS)

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey.svg)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)

A comprehensive, role-based Event Management System built to handle the entire lifecycle of professional events. This platform empowers organizers to create events, manage attendees, analyze real-time ticket sales, and generate automated PDF certificates.

## 🌟 Key Features

* **Role-Based Access Control (RBAC):** Distinct workflows for Attendees, Organizers, and System Administrators.
* **Real-Time Analytics:** Visual dashboards using Chart.js to track ticket sales and check-in ratios.
* **Seamless Check-in System:** One-click manual check-ins for event organizers.
* **Automated Certificate Generation:** Dynamically generated PDF attendance certificates (ReportLab).
* **Data Export:** Export attendee lists directly to CSV format for external CRM integrations.
* **Cloud Database:** Powered by Google Firebase Firestore for fast, NoSQL data management.
* **Containerized:** Fully containerized using Docker for consistent cross-platform deployment.

## 🏗️ System Architecture

* **Frontend:** HTML5, Bootstrap 5, Jinja2 Templating, Chart.js
* **Backend:** Python, Flask (Web Framework)
* **Database:** Firebase Firestore (NoSQL)
* **Authentication:** Firebase Auth / Custom Session Management
* **Infrastructure:** Docker & Docker Compose

## 🚀 Getting Started (Local Development)

### Prerequisites
* Docker and Docker Compose installed.
* A Firebase Project with Firestore enabled.
* A `serviceAccountKey.json` file from your Firebase console.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/event-management-system.git
   cd event-management-system