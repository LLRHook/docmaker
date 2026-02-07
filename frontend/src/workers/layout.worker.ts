import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";

cytoscape.use(fcose);

export interface LayoutRequest {
  elements: cytoscape.ElementDefinition[];
  options: Record<string, unknown>;
}

export interface LayoutResponse {
  positions: Record<string, { x: number; y: number }>;
}

self.onmessage = (e: MessageEvent<LayoutRequest>) => {
  const { elements, options } = e.data;

  const cy = cytoscape({
    headless: true,
    elements,
  });

  const layout = cy.layout(options as unknown as cytoscape.LayoutOptions);

  layout.on("layoutstop", () => {
    const positions: Record<string, { x: number; y: number }> = {};
    cy.nodes().forEach((node) => {
      positions[node.id()] = node.position();
    });
    (self as unknown as Worker).postMessage({ positions } satisfies LayoutResponse);
    cy.destroy();
  });

  layout.run();
};
