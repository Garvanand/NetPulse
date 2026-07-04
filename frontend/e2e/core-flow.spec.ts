import { test, expect } from '@playwright/test';

test.describe('NetPulse Core E2E Flow', () => {
  // Use mock authentication if we aren't spinning up the backend DB,
  // or simply bypass auth by going straight to the dashboard if it's permissive.
  
  test('User can navigate from Map to Incidents and read an LLM explanation', async ({ page }) => {
    // 1. Visit the root and ensure redirect to /dashboard (or map)
    await page.goto('/');
    
    // 2. Navigate to Live Map
    await page.click('text=Live Map');
    await expect(page).toHaveURL(/.*\/map/);
    
    // Ensure the Canvas/MapLibre container is rendered
    const mapContainer = page.locator('.maplibregl-canvas-container');
    await expect(mapContainer).toBeVisible({ timeout: 10000 });
    
    // 3. Navigate to Topology Graph
    await page.click('text=Topology');
    await expect(page).toHaveURL(/.*\/topology/);
    
    // Ensure the force-graph canvas is rendered
    const graphCanvas = page.locator('canvas');
    await expect(graphCanvas.first()).toBeVisible({ timeout: 10000 });
    
    // 4. Navigate to Incidents Dashboard
    await page.click('text=Incidents');
    await expect(page).toHaveURL(/.*\/incidents/);
    
    // 5. Select a Critical Incident
    const criticalIncidentBtn = page.locator('button', { hasText: 'CRITICAL' }).first();
    await expect(criticalIncidentBtn).toBeVisible({ timeout: 10000 });
    await criticalIncidentBtn.click();
    
    // 6. Verify LLM Explanation appears
    const explanationCard = page.locator('text=Anthropic Root Cause Analysis');
    await expect(explanationCard).toBeVisible({ timeout: 10000 });
    
    // Verify signal metrics appear
    await expect(page.locator('text=GNN Prediction Score')).toBeVisible();
    await expect(page.locator('text=Latency Z-Score')).toBeVisible();
  });
});
