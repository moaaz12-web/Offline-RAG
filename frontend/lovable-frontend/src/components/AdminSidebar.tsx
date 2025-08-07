import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Upload, Search, Trash2, FileText } from "lucide-react";
import { apiService } from "@/services/api";
import { toast } from "@/hooks/use-toast";

interface AdminSidebarProps {
  isOpen: boolean;
}

export const AdminSidebar = ({ isOpen }: AdminSidebarProps) => {
  const [uploading, setUploading] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearIndexName, setClearIndexName] = useState("");
  const [inspectData, setInspectData] = useState<any>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    setUploading(true);
    try {
      const result = await apiService.uploadDocuments(files);
      toast({
        title: "Upload Successful",
        description: `Uploaded ${files.length} documents successfully`,
      });
      console.log("Upload result:", result);
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
      // Clear the input
      event.target.value = "";
    }
  };

  const handleInspectStructure = async () => {
    setInspecting(true);
    try {
      const structure = await apiService.inspectStructure();
      setInspectData(structure);
      toast({
        title: "Structure Retrieved",
        description: "Weaviate structure fetched successfully",
      });
    } catch (error) {
      toast({
        title: "Inspect Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setInspecting(false);
    }
  };

  const handleClearIndex = async () => {
    setClearing(true);
    try {
      const result = await apiService.clearIndex(clearIndexName || undefined);
      toast({
        title: "Clear Successful",
        description: result.message,
      });
      console.log("Clear result:", result);
      setClearIndexName("");
    } catch (error) {
      toast({
        title: "Clear Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setClearing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="w-80 bg-slate-900 border-r border-slate-700 p-4 overflow-y-auto custom-scrollbar">
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
            Admin Panel
          </h2>
        </div>

        {/* Upload Section */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-white">
              <Upload className="w-4 h-4 text-blue-400" />
              Upload Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Label htmlFor="file-upload" className="text-xs text-slate-300">
                Choose documents (PDF, TXT, DOCX)
              </Label>
              <Input
                id="file-upload"
                type="file"
                multiple
                accept=".pdf,.txt,.docx"
                onChange={handleFileUpload}
                disabled={uploading}
                className="text-xs bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
              />
              {uploading && (
                <div className="text-xs text-slate-300 flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                  Uploading and processing...
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Separator className="bg-slate-700" />

        {/* Inspect Section */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-white">
              <Search className="w-4 h-4 text-green-400" />
              Inspect Structure
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleInspectStructure}
              disabled={inspecting}
              variant="outline"
              size="sm"
              className="w-full bg-slate-700 border-slate-600 text-white hover:bg-slate-600"
            >
              {inspecting ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                  Fetching...
                </div>
              ) : (
                "View Structure"
              )}
            </Button>

            {inspectData && (
              <div className="mt-3 p-2 bg-slate-700 rounded text-xs border border-slate-600">
                <div className="flex items-center gap-1 mb-2 text-slate-300">
                  <FileText className="w-3 h-3" />
                  Structure Data:
                </div>
                <div className="max-h-64 overflow-y-auto custom-scrollbar">
                  <pre className="whitespace-pre-wrap overflow-x-auto text-slate-200">
                    {JSON.stringify(inspectData, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Separator className="bg-slate-700" />

        {/* Clear Index Section */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-white">
              <Trash2 className="w-4 h-4 text-red-400" />
              Clear Index
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <Label htmlFor="index-name" className="text-xs text-slate-300">
                  Index name (leave blank for ALL)
                </Label>
                <Input
                  id="index-name"
                  value={clearIndexName}
                  onChange={(e) => setClearIndexName(e.target.value)}
                  placeholder="Enter index name..."
                  disabled={clearing}
                  className="text-xs mt-1 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
                />
              </div>
              <Button
                onClick={handleClearIndex}
                disabled={clearing}
                variant="destructive"
                size="sm"
                className="w-full bg-red-600 hover:bg-red-700"
              >
                {clearing ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                    Clearing...
                  </div>
                ) : (
                  "Clear Index"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};