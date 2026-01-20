import React, { useState, useEffect } from "react";

export default function ImageCard({ result, onClick }) {
  const [imgSrc, setImgSrc] = useState("");
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setImgSrc(result.url);
    setHasError(false);
  }, [result.url]);

const matchPercentage =
  result.score >= 0.92
    ? 100
    : Math.round(
        Math.min(100, Math.max(0, ((result.score - 0.3) / 0.7) * 100))
      );



  const handleError = () => {
    console.error("Image failed to load:", result.url);
    setHasError(true);
    setImgSrc(
      "https://placehold.co/400x400/e2e8f0/94a3b8?text=Image+Not+Found"
    );
  };

  return (
    <div
      onClick={onClick}
      className="group relative bg-white rounded-xl shadow-sm border overflow-hidden"
    >
      <div className="aspect-square bg-gray-100 flex items-center justify-center">
        {imgSrc && (
          <img
            src={imgSrc}
            alt={result.filename || "Image"}
            onError={handleError}
            className="w-full h-full object-cover transition-transform group-hover:scale-110"
            loading="lazy"
          />
        )}

        {matchPercentage !== null && !hasError && (
          <div className="absolute top-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded-full">
            {matchPercentage}% Match
          </div>
        )}
      </div>

      <div className="p-3">
        <p className="text-sm font-medium truncate">
          {result.filename || "Untitled"}
        </p>
      </div>
    </div>
  );
}
