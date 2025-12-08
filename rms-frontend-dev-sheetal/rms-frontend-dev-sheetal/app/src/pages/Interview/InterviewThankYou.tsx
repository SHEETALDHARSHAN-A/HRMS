import React from 'react'
import { useNavigate } from 'react-router-dom'

const InterviewThankYou: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow-md rounded-lg p-8 text-center max-w-lg">
        <h2 className="text-2xl font-semibold mb-4">Thank you!</h2>
        <p className="text-gray-600 mb-6">Thank you for attending the interview. We appreciate your time.</p>
        <div className="flex justify-center">
          <button
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            onClick={() => navigate('/')}
          >
            Return to Home
          </button>
        </div>
      </div>
    </div>
  )
}

export default InterviewThankYou
