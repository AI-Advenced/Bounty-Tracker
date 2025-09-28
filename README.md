# 🎯 Advanced Bounty Tracker

Une application web avancée de suivi des bounties GitHub, construite avec **FastAPI**, **SQLite**, et des fonctionnalités temps réel.

## 🌟 Fonctionnalités Principales

### 🔍 **Découverte et Suivi**
- **Recherche automatique** des bounties GitHub avec l'API GitHub
- **Détection intelligente** des montants de bounties dans les titres et descriptions
- **Suivi en temps réel** des nouvelles issues et mises à jour
- **Filtrage avancé** par langage, montant minimum, statut, repository

### 👥 **Système d'Utilisateurs**
- **Authentification JWT** complète avec tokens d'accès et de rafraîchissement
- **Rôles utilisateurs** : Admin, Modérateur, Maintainer, Hunter, User
- **Profils utilisateurs** avec statistiques de gains et réputation
- **Intégration GitHub** et Telegram pour les notifications

### 💰 **Gestion des Bounties**
- **Système de bounties** avec statuts (ouvert, réclamé, en cours, complété)
- **Suivi des paiements** et historique des transactions
- **Types de bounties** : bug fix, feature, documentation, tests, etc.
- **Critères d'acceptation** et gestion des deadlines

### 📊 **Analytics et Reporting**
- **Dashboard avancé** avec graphiques interactifs (Chart.js)
- **Statistiques détaillées** par langue, repository, période
- **Métriques de performance** et analytics d'utilisation
- **Exportation de données** et rapports personnalisés

### 🔔 **Notifications Temps Réel**
- **WebSocket** pour les mises à jour en temps réel
- **Notifications multi-canal** : Email, Telegram, Browser, Webhook
- **Préférences personnalisables** par type de notification
- **Heures de silence** et filtres par mots-clés

### 🔍 **Recherche et Filtrage**
- **Moteur de recherche** full-text avec suggestions
- **Filtres multiples** combinables
- **Recherche sauvegardée** et alertes personnalisées
- **API REST complète** avec pagination et tri

## 🏗️ Architecture Technique

### **Backend (Python/FastAPI)**
```
app/
├── main.py              # Application principale avec WebSocket
├── models/              # Modèles SQLAlchemy (8 tables principales)
│   ├── user.py         # Utilisateurs et authentification
│   ├── issue.py        # Issues GitHub et labels
│   ├── repository.py   # Repositories et statistiques
│   ├── bounty.py       # Bounties et paiements
│   ├── notification.py # Notifications multi-canal
│   └── search.py       # Recherche et analytics
├── services/           # Services métier
│   ├── github_service.py    # API GitHub avancée
│   ├── auth_service.py      # Authentification JWT
│   ├── notification_service.py # Notifications
│   └── telegram_service.py  # Bot Telegram
├── api/               # API REST endpoints
│   ├── issues.py      # CRUD issues avec pagination
│   ├── bounties.py    # Gestion des bounties
│   ├── auth.py        # Authentification
│   └── search.py      # Recherche avancée
└── templates/         # Templates Jinja2 modernes
    ├── base.html      # Layout avec Tailwind CSS
    └── dashboard/     # Dashboard interactif
```

### **Frontend (Moderne & Responsive)**
- **Tailwind CSS** pour le design moderne et responsive
- **Alpine.js** pour l'interactivité côté client
- **Chart.js** pour les graphiques et visualisations
- **WebSocket** pour les mises à jour temps réel
- **Progressive Web App** (PWA) ready

### **Base de Données (SQLite Optimisée)**
```sql
-- 8 tables principales avec relations complexes
users (authentification, profils, préférences)
repositories (projets GitHub, statistiques)  
issues (issues GitHub, bounties, métadonnées)
bounties (système de bounties complet)
notifications (multi-canal, préférences)
analytics_events (tracking d'usage)
search_queries (historique de recherche)
repository_stats (métriques historiques)
```

## 🚀 Installation et Démarrage

### **1. Installation des Dépendances**
```bash
cd /home/user/webapp
pip install -r requirements.txt
```

### **2. Initialisation de l'Application**
```bash
# Initialisation complète avec base de données
python init_app.py

# Ou avec des données d'exemple
python init_app.py --sample-data
```

### **3. Configuration (Optionnel)**
```bash
# Token GitHub pour l'API (recommandé)
export GITHUB_TOKEN='your_github_token_here'

# Bot Telegram pour notifications
export TELEGRAM_BOT_TOKEN='your_telegram_bot_token'
export TELEGRAM_CHAT_ID='your_chat_id'

# Configuration de sécurité
export SECRET_KEY='your-super-secret-key'
```

### **4. Démarrage de l'Application**
```bash
# Démarrage avec PM2 (recommandé)
pm2 start ecosystem.config.cjs

# Ou démarrage direct pour développement
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## 📱 Accès à l'Application

- **🌐 Interface Web**: http://localhost:3000
- **👤 Connexion Admin**: 
  - Username: `admin`
  - Password: `admin123`
- **📊 Dashboard**: Interface principale avec statistiques
- **🔍 API Documentation**: http://localhost:3000/docs (Swagger)
- **📈 Monitoring**: `pm2 logs bounty-tracker`

## 🎯 Points d'Entrée Principaux

### **Pages Web**
- `/` - Dashboard principal avec statistiques et graphiques
- `/issues` - Liste des issues avec filtres avancés
- `/repositories` - Catalogue des repositories
- `/bounties` - Gestion des bounties
- `/search` - Recherche avancée multi-critères
- `/profile` - Profil utilisateur et préférences

### **API REST Endpoints**
- `GET /api/issues` - Liste paginée des issues
- `GET /api/issues/{id}` - Détails d'une issue
- `POST /api/auth/login` - Authentification utilisateur
- `GET /api/search/issues` - Recherche avancée
- `GET /api/analytics/summary` - Statistiques générales
- `WebSocket /ws` - Connexion temps réel

## 🔧 Fonctionnalités Avancées

### **Recherche et Filtrage**
- Recherche full-text dans titres et descriptions
- Filtres par: langue, montant min/max, statut, repository
- Tri par: date, montant, popularité, tendance
- Suggestions de recherche en temps réel
- Sauvegarde des recherches favorites

### **Système de Notifications**
- **Email** : Notifications par email avec templates HTML
- **Telegram** : Bot Telegram pour alertes instantanées  
- **Browser** : Notifications push dans le navigateur
- **WebSocket** : Mises à jour temps réel de l'interface

### **Analytics et Métriques**
- Suivi des vues et interactions utilisateurs
- Statistiques des bounties par période et langue
- Métriques de performance des repositories
- Rapports d'activité et tableaux de bord

### **Sécurité**
- Authentification JWT avec refresh tokens
- Hashage sécurisé des mots de passe (bcrypt)
- Protection CORS et validation des entrées
- Gestion granulaire des permissions par rôle

## 📈 Statistiques du Projet

- **📝 Lignes de Code**: 6000+ lignes
- **🗃️ Modèles de Données**: 8 tables interconnectées
- **🔌 API Endpoints**: 25+ endpoints REST
- **🎨 Templates**: Interface moderne responsive
- **⚡ Services**: 7 services métier spécialisés
- **🧪 Fonctionnalités**: Plus de 30 fonctionnalités majeures

## 🔄 Prochaines Étapes de Développement

1. **🔗 Intégrations Externes**
   - Intégration avec Bountysource, Gitcoin, Algora
   - Support des crypto-paiements
   - API webhooks pour notifications externes

2. **🤖 Intelligence Artificielle**
   - Recommandation personnalisée de bounties
   - Détection automatique de la difficulté
   - Analyse sentimentale des commentaires

3. **📱 Applications Mobiles**
   - PWA complète avec notifications push
   - Application mobile native (Flutter/React Native)
   - Support hors-ligne et synchronisation

4. **🎯 Fonctionnalités Sociales**
   - Système de réputation et badges
   - Équipes et collaboration
   - Marketplace de services

## 🛠️ Maintenance et Support

### **Commandes Utiles**
```bash
# Logs et monitoring
pm2 logs bounty-tracker         # Voir les logs
pm2 restart bounty-tracker      # Redémarrer
pm2 stop bounty-tracker         # Arrêter

# Base de données
python -c "from app.db import get_db_stats; print(get_db_stats())"

# Synchronisation GitHub manuelle
curl -X POST http://localhost:3000/api/admin/sync-github
```

### **Configuration de Production**
- Configurer un reverse proxy (nginx)
- Utiliser une base de données PostgreSQL
- Configurer SSL/TLS (Let's Encrypt)
- Mettre en place monitoring (Prometheus/Grafana)
- Sauvegardes automatiques des données

### **Fonctionnalités Déployées**
- ✅ **Dashboard interactif** avec statistiques en temps réel
- ✅ **Liste des issues** avec bounties GitHub
- ✅ **Base de données SQLite** avec données d'exemple
- ✅ **API REST** pour les données JSON
- ✅ **Interface responsive** avec Tailwind CSS
- ✅ **Navigation intuitive** et design moderne

## 📊 État Actuel du Déploiement

- **✅ Statut**: **DÉPLOYÉ ET FONCTIONNEL**
- **🏗️ Plateforme**: Python/FastAPI + SQLite  
- **🔧 Tech Stack**: Modern web stack avec PM2
- **📅 Dernière Mise à Jour**: 28 septembre 2024
- **🎯 Version**: 2.0.0 (Version avancée avec 6000+ lignes)

---

**🎉 Cette application Bounty Tracker offre une solution complète et professionnelle pour le suivi des bounties GitHub avec plus de 6000 lignes de code et des fonctionnalités avancées temps réel !**
