import { useState, useRef } from "react";
import { uploadImages } from "../services/api";

export default function Upload() {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState("idle"); // or uploading or success

  // 0=Idle, 1=Saving, 2=Preprocessing, 3=Embedding, 4=FAISS, 5=Done
  const [currStep, setCurrStep] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef(null);

  //Batch uploading setup
  const [progress, setProgress] = useState({ processed: 0, total: 0 });

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (incomingFiles) => {
    const newFilesArray = Array.from(incomingFiles);

    const validFiles = newFilesArray.filter((file) =>
      ["image/jpeg", "image/png", "image/jpg"].includes(file.type),
    );

    if (validFiles.length !== newFilesArray.length) {
      setErrorMsg("Some files were skipped. Only JPG and PNG allowed.");
    } else {
      setErrorMsg("");
    }

    setFiles((prev) => [...prev, ...validFiles]);
    setStatus("idle");
    setCurrStep(0);
  };

  const removeFile = (indexToRemove) => {
    setFiles((prev) => prev.filter((_, index) => index !== indexToRemove));
  };

  /*
  Work of HandleUpload:
    Take the selected files →
    call backend →
    show visual pipeline progress →
    handle success/failure
  */
  const handleUpload = async () => {
    if (!fileInputRef.current?.files?.length) return;

    setStatus("uploading");
    setErrorMsg("");
    setCurrStep(1); //Images Saved (pending)

    const fileList = Array.from(fileInputRef.current.files);
    const totalFiles = fileList.length;
    const MAX_BATCH_SIZE = 50;

    setProgress({ processed: 0, total: totalFiles });

    try {
      let processedCount = 0;
      let firstBatchDone = false;
      for (let i = 0; i < totalFiles; i += MAX_BATCH_SIZE) {
        const chunk = fileList.slice(i, i + MAX_BATCH_SIZE);

        await uploadImages(chunk);

        processedCount += chunk.length;
        setProgress({ processed: processedCount, total: totalFiles });

        //steps transitions
        if (!firstBatchDone) {
          //First successful batch-> images are saved
          setCurrStep(2); //Preprocessing
          firstBatchDone = true;
        }
        else {

          const percent = (processedCount / totalFiles) * 100;

          let step;
          if (percent <50) step = 2; //preprocessing
          else if (percent < 70) step = 3; //embedding
          else step = 4; //FAISS update

          setCurrStep(step);
        }

        // allow browser to release memory between batches
        await new Promise((r) => setTimeout(r, 50));
      }

      setCurrStep(5);
      setStatus("success");

      // cleanup
      setTimeout(() => {
        setFiles([]);
        setCurrStep(0);
        setProgress({ processed: 0, total: 0 });
        if (fileInputRef.current) fileInputRef.current.value = "";
      }, 1000);
    } catch (error) {
      console.error("Batch upload failed:", error);
      setStatus("idle");
      setErrorMsg("Upload failed. Please try again.");
    }
  };

  // Helper to determine step status
  const getStepStatus = (stepIndex) => {
    if (currStep > stepIndex) return "completed";
    if (currStep === stepIndex) return "active";
    return "waiting";
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto p-4">
      <div className="text-center md:text-left">
        <h2 className="text-3xl font-bold text-gray-900">Upload Images</h2>
        <p className="text-gray-500 mt-2 text-lg">
          Add images to build your visual search index.
        </p>
      </div>

      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-colors min-h-[300px]
          ${dragActive ? "border-indigo-500 bg-indigo-50" : "border-gray-300 bg-white"}
          ${status === "uploading" ? "opacity-50 pointer-events-none" : ""}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          id="file-upload"
          className="hidden"
          onChange={handleChange}
          accept="image/png, image/jpeg, image/jpg"
        />

        {files.length > 0 ? (
          <div className="w-full max-w-lg mb-6">
            <div className="flex justify-between items-center mb-2 px-1">
              <span className="text-sm font-medium text-gray-700">
                {files.length} files selected
              </span>
              <button
                onClick={() => setFiles([])}
                className="text-xs text-red-500 hover:text-red-700 hover:underline"
              >
                Clear all
              </button>
            </div>

            <div className="max-h-60 overflow-y-auto pr-2 custom-scrollbar space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-gray-50 p-2 rounded border border-gray-200"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 bg-indigo-100 rounded flex flex-shrink-0 items-center justify-center">
                      <svg
                        className="w-4 h-4 text-indigo-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(0)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center mb-6">
            <div className="bg-indigo-100 p-4 rounded-full mb-4 inline-block">
              <svg
                className="w-8 h-8 text-indigo-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <p className="text-lg font-medium text-gray-900">
              <label
                htmlFor="file-upload"
                className="cursor-pointer text-indigo-600 hover:text-indigo-500 hover:underline"
              >
                Click to upload
              </label>{" "}
              or drag and drop
            </p>
            <p className="text-sm text-gray-500 mt-1">
              PNG, JPG (max. 5MB per file)
            </p>
          </div>
        )}

        <div className="flex flex-col items-center gap-2">
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || status === "uploading"}
            className={`px-8 py-3 rounded-lg text-white font-medium transition-all
                    ${files.length === 0 || status === "uploading"
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-700 shadow-lg hover:shadow-indigo-500/30"
              }
                `}
          >
            {status === "uploading"
              ? `Uploading ${files.length} images...`
              : "Start Upload"}
          </button>
          {/* Add more button when files are present */}
          {files.length > 0 && (
            <label
              htmlFor="file-upload"
              className="cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 font-medium mt-2"
            >
              + Add more images
            </label>
          )}
        </div>

        {errorMsg && (
          <p className="mt-4 text-red-500 text-sm bg-red-50 px-3 py-1 rounded">
            {errorMsg}
          </p>
        )}
      </div>

      {/* Visual Pipeline */}
      <div className="grid md:grid-cols-4 gap-4">
        <PipelineStep
          label="Images Saved"
          status={getStepStatus(1)}
          icon={
            <svg
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
              />
            </svg>
          }
        />
        <PipelineStep
          label="Preprocessing"
          status={getStepStatus(2)}
          icon={
            <svg
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
              />
            </svg>
          }
        />
        <PipelineStep
          label="Embedding Gen"
          status={getStepStatus(3)}
          icon={
            <svg
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          }
        />
        <PipelineStep
          label="FAISS Update"
          status={getStepStatus(4)}
          icon={
            <svg
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
              />
            </svg>
          }
        />
      </div>

      {status === "success" && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 flex items-start gap-4 animate-fade-in-up">
          <div className="bg-green-100 p-2 rounded-full">
            <svg
              className="w-6 h-6 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-green-800 font-semibold text-lg">
              Batch Upload Successful!
            </h3>
            <p className="text-green-600 mt-1">
              All valid images have been processed and added to the visual
              search index.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function PipelineStep({ label, status, icon }) {
  // status: 'waiting' | 'active' | 'completed'

  const baseClasses =
    "relative p-6 rounded-xl border-2 transition-all duration-500";

  const statusClasses = {
    waiting: "border-gray-100 bg-white opacity-60",
    active: "border-indigo-500 bg-indigo-50 shadow-md transform scale-105",
    completed: "border-indigo-600 bg-indigo-50", // Solid indigo for completed
  };

  const iconColors = {
    waiting: "text-gray-400",
    active: "text-indigo-600",
    completed: "text-indigo-700",
  };

  const textColors = {
    waiting: "text-gray-500",
    active: "text-indigo-900",
    completed: "text-indigo-900",
  };

  return (
    <div className={`${baseClasses} ${statusClasses[status]}`}>
      <div className={`mb-3 ${iconColors[status]}`}>{icon}</div>
      <h3 className={`font-semibold ${textColors[status]}`}>{label}</h3>

      {/* Active State Pulse */}
      {status === "active" && (
        <div className="absolute top-4 right-4">
          <span className="flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
          </span>
        </div>
      )}

      {/* Completed State Checkmark */}
      {status === "completed" && (
        <div className="absolute top-4 right-4 bg-indigo-600 rounded-full p-1">
          <svg
            className="w-3 h-3 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
      )}
    </div>
  );
}
