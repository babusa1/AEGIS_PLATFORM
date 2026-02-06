'use client';

import ReactFlowBuilder from '@/components/workflow/ReactFlowBuilder';

export default function FlowBuilderPage() {
  const handleSave = (nodes: any[], edges: any[]) => {
    console.log('Saving workflow:', { nodes, edges });
    // TODO: Call API to save workflow
  };

  const handleExecute = (nodes: any[], edges: any[]) => {
    console.log('Executing workflow:', { nodes, edges });
    // TODO: Call API to execute workflow
  };

  return (
    <div className="h-screen">
      <ReactFlowBuilder
        onSave={handleSave}
        onExecute={handleExecute}
      />
    </div>
  );
}
