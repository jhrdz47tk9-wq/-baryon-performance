# BARYON Performance

Aplicación independiente de Wet-Box. Ruta raíz: captura de escenarios de BARYON/OEE/EBITDA, clasificación de evidencia, revisión NO GO y exportación JSON. No contiene modelos propietarios ni calcula resultados ficticios.

Estado: frontend inicial; API responde 503 explícito. No existe conexión al backend de Wet-Box. Falta contrato e identidad del servicio propio en Google Cloud.

Arquitectura objetivo: navegador → frontend/BFF Vercel → API privada Google Cloud. Modelos, persistencia y auditoría en Google Cloud; GitHub como fuente versionada y CI. No usar tokens de usuario ni claves privadas en el navegador. Autenticación de usuario, autorización por planta y federación de identidad entre plataformas pendientes antes de activar consultas reales.

Desarrollo: npm install; npm run build. No hay secretos incluidos.

Origen: patrón Next.js de jhrdz47tk9-wq/-baryon-wetbox-ui; formulario recuperado de feat/baryon-performance-workspace. Wet-Box no se modifica.
