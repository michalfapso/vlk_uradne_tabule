import React, { useState } from 'react';
import { PrimeReactProvider } from 'primereact/api';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';

export default function PrimeReactTest() {
    const [text, setText] = useState('');

    const greet = () => {
        alert('PrimeReact is working! You typed: ' + text);
    };

    return (
        <PrimeReactProvider value={{ unstyled: true }}>
            <div className="card flex flex-col items-center gap-4 p-6 border rounded-xl bg-white shadow-lg max-w-md mx-auto my-8">
                <h3 className="text-2xl font-bold text-gray-800">PrimeReact Unstyled Test</h3>
                <div className="flex flex-col gap-2 w-full text-black">
                    <label htmlFor="username" className="font-semibold text-gray-700">Username</label>
                    <InputText 
                        id="username" 
                        value={text} 
                        onChange={(e) => setText(e.target.value)} 
                        placeholder="Enter username" 
                        pt={{
                            root: { className: 'p-2 border border-gray-300 rounded w-full' }
                        }}
                    />
                </div>
                <Button 
                    label="Submit" 
                    onClick={greet} 
                    pt={{
                        root: { className: 'w-full bg-blue-600 text-white font-bold py-2 px-4 rounded hover:bg-blue-700 transition-colors' },
                        label: { className: 'font-bold' }
                    }}
                />
                {text && <p className="text-green-600 font-medium mt-2">Reactivity check: {text}</p>}
            </div>
        </PrimeReactProvider>
    );
}
