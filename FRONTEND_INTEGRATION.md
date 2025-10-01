# Integración del Dashboard desde Frontend

## 📋 Resumen

Esta guía explica cómo consumir el API del dashboard de ratios desde cualquier frontend (React, Vue, Angular, vanilla JavaScript, etc.).

---

## 🌐 Endpoints Disponibles

### Endpoint Principal
```
GET http://localhost:8000/api/ratios/dashboard
```

**Respuesta:**
```json
{
  "status": "success",
  "data": [
    {
      "par": "AL30D-AL30C",
      "ultimo_ratio_operado": 1.03399,
      "promedio_rueda": 1.02424,
      "dif_rueda_pct": 0.95,
      "promedio_1semana": 1.01606,
      "dif_1semana_pct": 1.76,
      "promedio_1mes": 1.00740,
      "dif_1mes_pct": 2.64,
      "minimo_mensual": 0.99759,
      "dif_minimo_pct": 3.52,
      "maximo_mensual": 1.02657,
      "dif_maximo_pct": 0.72
    }
  ],
  "count": 13,
  "query_time_ms": 8.5,
  "method": "materialized_view",
  "freshness": "~10 seconds"
}
```

### Endpoints Alternativos

```
GET /api/ratios/dashboard/fast       # Vista materializada (<10ms)
GET /api/ratios/dashboard/balanced   # Función PostgreSQL (100-500ms)
GET /api/ratios/dashboard/flexible   # Python puro (500-2000ms)
```

---

## 🚀 Ejemplos de Integración

### 1. JavaScript Vanilla (Fetch API)

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard de Ratios</title>
    <style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
        th { background-color: #4CAF50; color: white; }
        .positive { color: green; }
        .negative { color: red; }
    </style>
</head>
<body>
    <h1>Dashboard de Ratios en Tiempo Real</h1>
    <div id="status">Cargando...</div>
    <table id="ratios-table">
        <thead>
            <tr>
                <th>Par</th>
                <th>Último Ratio</th>
                <th>Rueda Anterior</th>
                <th>1 Semana</th>
                <th>1 Mes</th>
                <th>Mín Mensual</th>
                <th>Máx Mensual</th>
            </tr>
        </thead>
        <tbody id="ratios-body"></tbody>
    </table>

    <script>
        const API_URL = 'http://localhost:8000/api/ratios/dashboard';
        
        async function fetchRatios() {
            try {
                const response = await fetch(API_URL);
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateTable(data.data);
                    updateStatus(data);
                } else {
                    console.error('Error:', data);
                }
            } catch (error) {
                console.error('Error fetching ratios:', error);
                document.getElementById('status').textContent = 'Error al cargar datos';
            }
        }
        
        function updateTable(ratios) {
            const tbody = document.getElementById('ratios-body');
            tbody.innerHTML = '';
            
            ratios.forEach(ratio => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td><strong>${ratio.par}</strong></td>
                    <td>${ratio.ultimo_ratio_operado.toFixed(5)}</td>
                    <td class="${ratio.dif_rueda_pct >= 0 ? 'positive' : 'negative'}">
                        ${ratio.promedio_rueda?.toFixed(5) || 'N/A'}
                        (${ratio.dif_rueda_pct >= 0 ? '+' : ''}${ratio.dif_rueda_pct}%)
                    </td>
                    <td class="${ratio.dif_1semana_pct >= 0 ? 'positive' : 'negative'}">
                        ${ratio.promedio_1semana?.toFixed(5) || 'N/A'}
                        (${ratio.dif_1semana_pct >= 0 ? '+' : ''}${ratio.dif_1semana_pct}%)
                    </td>
                    <td class="${ratio.dif_1mes_pct >= 0 ? 'positive' : 'negative'}">
                        ${ratio.promedio_1mes?.toFixed(5) || 'N/A'}
                        (${ratio.dif_1mes_pct >= 0 ? '+' : ''}${ratio.dif_1mes_pct}%)
                    </td>
                    <td>${ratio.minimo_mensual?.toFixed(5) || 'N/A'}</td>
                    <td>${ratio.maximo_mensual?.toFixed(5) || 'N/A'}</td>
                `;
            });
        }
        
        function updateStatus(data) {
            const status = document.getElementById('status');
            status.textContent = `Última actualización: ${new Date().toLocaleTimeString()} | ` +
                                `${data.count} pares | ` +
                                `${data.query_time_ms}ms | ` +
                                `Frescura: ${data.freshness}`;
        }
        
        // Actualizar cada 10 segundos
        fetchRatios();
        setInterval(fetchRatios, 10000);
    </script>
</body>
</html>
```

---

### 2. React

```jsx
import React, { useState, useEffect } from 'react';
import './Dashboard.css';

const API_URL = 'http://localhost:8000/api/ratios/dashboard';

function Dashboard() {
  const [ratios, setRatios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [queryTime, setQueryTime] = useState(null);

  useEffect(() => {
    const fetchRatios = async () => {
      try {
        const response = await fetch(API_URL);
        const data = await response.json();
        
        if (data.status === 'success') {
          setRatios(data.data);
          setQueryTime(data.query_time_ms);
          setLastUpdate(new Date());
          setError(null);
        } else {
          setError('Error al cargar datos');
        }
      } catch (err) {
        setError('Error de conexión: ' + err.message);
      } finally {
        setLoading(false);
      }
    };

    // Fetch inicial
    fetchRatios();

    // Actualizar cada 10 segundos
    const interval = setInterval(fetchRatios, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Cargando...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="dashboard">
      <h1>Dashboard de Ratios</h1>
      <div className="status">
        Última actualización: {lastUpdate?.toLocaleTimeString()} | 
        {ratios.length} pares | 
        {queryTime}ms
      </div>

      <table className="ratios-table">
        <thead>
          <tr>
            <th>Par</th>
            <th>Último Ratio</th>
            <th>Rueda Anterior</th>
            <th>1 Semana</th>
            <th>1 Mes</th>
            <th>Mín Mensual</th>
            <th>Máx Mensual</th>
          </tr>
        </thead>
        <tbody>
          {ratios.map((ratio) => (
            <RatioRow key={ratio.par} ratio={ratio} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RatioRow({ ratio }) {
  const getColorClass = (value) => value >= 0 ? 'positive' : 'negative';

  return (
    <tr>
      <td><strong>{ratio.par}</strong></td>
      <td>{ratio.ultimo_ratio_operado.toFixed(5)}</td>
      <td className={getColorClass(ratio.dif_rueda_pct)}>
        {ratio.promedio_rueda?.toFixed(5) || 'N/A'}
        <br />
        <span className="diff">
          ({ratio.dif_rueda_pct >= 0 ? '+' : ''}{ratio.dif_rueda_pct}%)
        </span>
      </td>
      <td className={getColorClass(ratio.dif_1semana_pct)}>
        {ratio.promedio_1semana?.toFixed(5) || 'N/A'}
        <br />
        <span className="diff">
          ({ratio.dif_1semana_pct >= 0 ? '+' : ''}{ratio.dif_1semana_pct}%)
        </span>
      </td>
      <td className={getColorClass(ratio.dif_1mes_pct)}>
        {ratio.promedio_1mes?.toFixed(5) || 'N/A'}
        <br />
        <span className="diff">
          ({ratio.dif_1mes_pct >= 0 ? '+' : ''}{ratio.dif_1mes_pct}%)
        </span>
      </td>
      <td>{ratio.minimo_mensual?.toFixed(5) || 'N/A'}</td>
      <td>{ratio.maximo_mensual?.toFixed(5) || 'N/A'}</td>
    </tr>
  );
}

export default Dashboard;
```

**CSS (Dashboard.css):**
```css
.dashboard {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.status {
  background: #f0f0f0;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
}

.ratios-table {
  width: 100%;
  border-collapse: collapse;
}

.ratios-table th,
.ratios-table td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: right;
}

.ratios-table th {
  background-color: #4CAF50;
  color: white;
}

.positive {
  color: #4CAF50;
  font-weight: bold;
}

.negative {
  color: #f44336;
  font-weight: bold;
}

.diff {
  font-size: 0.9em;
}

.error {
  color: red;
  padding: 20px;
  background: #ffe6e6;
  border-radius: 5px;
}
```

---

### 3. Vue.js 3

```vue
<template>
  <div class="dashboard">
    <h1>Dashboard de Ratios</h1>
    
    <div v-if="loading" class="loading">Cargando...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <template v-else>
      <div class="status">
        Última actualización: {{ lastUpdate }} | 
        {{ ratios.length }} pares | 
        {{ queryTime }}ms
      </div>

      <table class="ratios-table">
        <thead>
          <tr>
            <th>Par</th>
            <th>Último Ratio</th>
            <th>Rueda Anterior</th>
            <th>1 Semana</th>
            <th>1 Mes</th>
            <th>Mín Mensual</th>
            <th>Máx Mensual</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ratio in ratios" :key="ratio.par">
            <td><strong>{{ ratio.par }}</strong></td>
            <td>{{ formatNumber(ratio.ultimo_ratio_operado) }}</td>
            <td :class="getColorClass(ratio.dif_rueda_pct)">
              {{ formatNumber(ratio.promedio_rueda) }}
              <br />
              <span class="diff">({{ formatPercent(ratio.dif_rueda_pct) }})</span>
            </td>
            <td :class="getColorClass(ratio.dif_1semana_pct)">
              {{ formatNumber(ratio.promedio_1semana) }}
              <br />
              <span class="diff">({{ formatPercent(ratio.dif_1semana_pct) }})</span>
            </td>
            <td :class="getColorClass(ratio.dif_1mes_pct)">
              {{ formatNumber(ratio.promedio_1mes) }}
              <br />
              <span class="diff">({{ formatPercent(ratio.dif_1mes_pct) }})</span>
            </td>
            <td>{{ formatNumber(ratio.minimo_mensual) }}</td>
            <td>{{ formatNumber(ratio.maximo_mensual) }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const API_URL = 'http://localhost:8000/api/ratios/dashboard';

const ratios = ref([]);
const loading = ref(true);
const error = ref(null);
const lastUpdate = ref('');
const queryTime = ref(0);
let intervalId = null;

const fetchRatios = async () => {
  try {
    const response = await fetch(API_URL);
    const data = await response.json();
    
    if (data.status === 'success') {
      ratios.value = data.data;
      queryTime.value = data.query_time_ms;
      lastUpdate.value = new Date().toLocaleTimeString();
      error.value = null;
    } else {
      error.value = 'Error al cargar datos';
    }
  } catch (err) {
    error.value = 'Error de conexión: ' + err.message;
  } finally {
    loading.value = false;
  }
};

const formatNumber = (value) => {
  return value != null ? value.toFixed(5) : 'N/A';
};

const formatPercent = (value) => {
  if (value == null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value}%`;
};

const getColorClass = (value) => {
  if (value == null) return '';
  return value >= 0 ? 'positive' : 'negative';
};

onMounted(() => {
  fetchRatios();
  intervalId = setInterval(fetchRatios, 10000);
});

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});
</script>

<style scoped>
/* Mismo CSS que el ejemplo de React */
</style>
```

---

### 4. Angular

**dashboard.component.ts:**
```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface Ratio {
  par: string;
  ultimo_ratio_operado: number;
  promedio_rueda: number;
  dif_rueda_pct: number;
  promedio_1semana: number;
  dif_1semana_pct: number;
  promedio_1mes: number;
  dif_1mes_pct: number;
  minimo_mensual: number;
  dif_minimo_pct: number;
  maximo_mensual: number;
  dif_maximo_pct: number;
}

interface DashboardResponse {
  status: string;
  data: Ratio[];
  count: number;
  query_time_ms: number;
  freshness: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  private readonly API_URL = 'http://localhost:8000/api/ratios/dashboard';
  private subscription?: Subscription;

  ratios: Ratio[] = [];
  loading = true;
  error: string | null = null;
  lastUpdate: string = '';
  queryTime: number = 0;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    // Fetch inicial y cada 10 segundos
    this.subscription = interval(10000)
      .pipe(switchMap(() => this.http.get<DashboardResponse>(this.API_URL)))
      .subscribe({
        next: (data) => {
          if (data.status === 'success') {
            this.ratios = data.data;
            this.queryTime = data.query_time_ms;
            this.lastUpdate = new Date().toLocaleTimeString();
            this.error = null;
          }
          this.loading = false;
        },
        error: (err) => {
          this.error = 'Error al cargar datos: ' + err.message;
          this.loading = false;
        }
      });

    // Fetch inicial inmediato
    this.http.get<DashboardResponse>(this.API_URL).subscribe({
      next: (data) => {
        if (data.status === 'success') {
          this.ratios = data.data;
          this.queryTime = data.query_time_ms;
          this.lastUpdate = new Date().toLocaleTimeString();
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al cargar datos: ' + err.message;
        this.loading = false;
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  getColorClass(value: number | null): string {
    if (value == null) return '';
    return value >= 0 ? 'positive' : 'negative';
  }

  formatNumber(value: number | null): string {
    return value != null ? value.toFixed(5) : 'N/A';
  }

  formatPercent(value: number | null): string {
    if (value == null) return 'N/A';
    return `${value >= 0 ? '+' : ''}${value}%`;
  }
}
```

**dashboard.component.html:**
```html
<div class="dashboard">
  <h1>Dashboard de Ratios</h1>
  
  <div *ngIf="loading" class="loading">Cargando...</div>
  <div *ngIf="error" class="error">{{ error }}</div>
  
  <ng-container *ngIf="!loading && !error">
    <div class="status">
      Última actualización: {{ lastUpdate }} | 
      {{ ratios.length }} pares | 
      {{ queryTime }}ms
    </div>

    <table class="ratios-table">
      <thead>
        <tr>
          <th>Par</th>
          <th>Último Ratio</th>
          <th>Rueda Anterior</th>
          <th>1 Semana</th>
          <th>1 Mes</th>
          <th>Mín Mensual</th>
          <th>Máx Mensual</th>
        </tr>
      </thead>
      <tbody>
        <tr *ngFor="let ratio of ratios">
          <td><strong>{{ ratio.par }}</strong></td>
          <td>{{ formatNumber(ratio.ultimo_ratio_operado) }}</td>
          <td [ngClass]="getColorClass(ratio.dif_rueda_pct)">
            {{ formatNumber(ratio.promedio_rueda) }}
            <br />
            <span class="diff">({{ formatPercent(ratio.dif_rueda_pct) }})</span>
          </td>
          <td [ngClass]="getColorClass(ratio.dif_1semana_pct)">
            {{ formatNumber(ratio.promedio_1semana) }}
            <br />
            <span class="diff">({{ formatPercent(ratio.dif_1semana_pct) }})</span>
          </td>
          <td [ngClass]="getColorClass(ratio.dif_1mes_pct)">
            {{ formatNumber(ratio.promedio_1mes) }}
            <br />
            <span class="diff">({{ formatPercent(ratio.dif_1mes_pct) }})</span>
          </td>
          <td>{{ formatNumber(ratio.minimo_mensual) }}</td>
          <td>{{ formatNumber(ratio.maximo_mensual) }}</td>
        </tr>
      </tbody>
    </table>
  </ng-container>
</div>
```

---

## 🔐 CORS (Cross-Origin Resource Sharing)

Si tu frontend está en un dominio diferente, necesitas habilitar CORS en el backend.

**Agregar en `main.py`:**

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React
        "http://localhost:8080",  # Vue
        "http://localhost:4200",  # Angular
        "https://tu-dominio.com"  # Producción
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Para desarrollo (permitir todos los orígenes):**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Solo para desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Componente Reutilizable (React Hooks)

```jsx
// hooks/useRatios.js
import { useState, useEffect } from 'react';

export function useRatios(apiUrl, refreshInterval = 10000) {
  const [ratios, setRatios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState({});

  useEffect(() => {
    const fetchRatios = async () => {
      try {
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (data.status === 'success') {
          setRatios(data.data);
          setMetadata({
            count: data.count,
            queryTime: data.query_time_ms,
            freshness: data.freshness,
            method: data.method,
            lastUpdate: new Date()
          });
          setError(null);
        } else {
          setError('Error al cargar datos');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRatios();
    const interval = setInterval(fetchRatios, refreshInterval);

    return () => clearInterval(interval);
  }, [apiUrl, refreshInterval]);

  return { ratios, loading, error, metadata };
}

// Uso:
import { useRatios } from './hooks/useRatios';

function Dashboard() {
  const { ratios, loading, error, metadata } = useRatios(
    'http://localhost:8000/api/ratios/dashboard',
    10000  // Actualizar cada 10 segundos
  );

  // ... resto del componente
}
```

---

## 🎨 Bibliotecas de UI Recomendadas

### Para tablas avanzadas:

**React:**
- [Material-UI DataGrid](https://mui.com/x/react-data-grid/)
- [AG Grid](https://www.ag-grid.com/)
- [TanStack Table](https://tanstack.com/table)

**Vue:**
- [Vuetify Data Tables](https://vuetifyjs.com/en/components/data-tables/)
- [Element Plus Table](https://element-plus.org/en-US/component/table.html)

**Angular:**
- [Angular Material Table](https://material.angular.io/components/table)
- [PrimeNG Table](https://primeng.org/table)

---

## 📱 Ejemplo con WebSocket (Tiempo Real)

Si necesitas datos en tiempo real inmediato (sin polling), considera WebSocket:

```javascript
// WebSocket connection (si implementas en el backend)
const ws = new WebSocket('ws://localhost:8000/ws/ratios');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'ratio_update') {
    updateRatioInTable(data.ratio);
  }
};
```

---

## 🔄 Resumen

| Frontend | Ejemplo Incluido | Complejidad |
|----------|------------------|-------------|
| **JavaScript Vanilla** | ✅ | ⭐ Fácil |
| **React** | ✅ | ⭐⭐ Media |
| **Vue 3** | ✅ | ⭐⭐ Media |
| **Angular** | ✅ | ⭐⭐⭐ Media-Alta |

Todos los ejemplos:
- ✅ Actualización automática cada 10 segundos
- ✅ Formateo de números y porcentajes
- ✅ Colores para diferencias positivas/negativas
- ✅ Manejo de errores
- ✅ Estado de carga

---

## 🚀 Próximos Pasos

1. Copiar el ejemplo de tu framework favorito
2. Ajustar la URL del API si es necesario
3. Personalizar estilos según tu diseño
4. ¡Disfrutar de tu dashboard en tiempo real!

