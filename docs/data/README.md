# 📊 Data Sources Documentation

Ce dossier contient la documentation détaillée des sources de données identifiées et analysées pour le projet AI-OPS Application Integrity.

## 📋 Index des sources documentées

### ✅ Sources analysées

- **[Index Kubernetes Audit Events](./elasticsearch_k8s_index_discovery.md)**
  - **Status :** ✅ Analysé en détail  
  - **Index :** `datalab-logs-audit-k8s`
  - **Description :** Événements d'audit Kubernetes enrichis avec métadonnées business (dws.*) et techniques (kubernetes.*)
  - **Volumétrie :** ~70K événements/15min
  - **Questions ouvertes :** Hiérarchie des codes AP, différenciation client/produit/plateforme

- **[Discovery Topology](./discovery_topology.md)**
  - **Status :** ✅ Analysé - Échantillon reçu et documenté
  - **Index :** ElasticSearch Cluster STA03
  - **API :** SV Reporting Tool (API2363)
  - **Description :** Topologie infrastructure (4 composants : ESX vCenter, Software Instance, NetworkDevices/LB/Storage, Kubernetes)
  - **Couverture :** Support des questions Q1-Q10 (topologie et dépendances) - MAIS éléments réseau seulement (pas flux communication)
  - **Limitation :** Contient IP, interfaces, VLAN, switches mais PAS les flux applicatifs
  - **Access :** https://yyy.intra:9200

### 🔄 Sources en cours d'analyse

- **Index Legacy VM Events**
  - **Status :** 🔄 Configuration en cours
  - **Index :** ElasticSearch Cluster Guillaume
  - **API :** Twin (ex Eureka)
  - **Collection :** LAAS Agent ES

- ** Illumio Network Flow**
  - **Status :** Collecte en cours
  - **API :** Illumio
  

## 🎯 Méthodologie de documentation

Chaque source de données documentée suit cette structure :
1. **Vue d'ensemble** : Contexte, grain, volumétrie
2. **Architecture des données** : Structure complète des objets
3. **Dimensions analytics** : Business, techniques, acteur
4. **Cas d'usage** : Questions supportées et patterns d'analyse
5. **Points d'attention** : Questions ouvertes et recommandations
6. **Impact architecture** : Intégration avec les agents

## 🔗 Liens connexes

- [Context principal](../context.md)
- [Architecture système](../confluence/confluence_system_architecture.md)
- [État actuel du projet](../../memory_bank/current_state.md)

---


