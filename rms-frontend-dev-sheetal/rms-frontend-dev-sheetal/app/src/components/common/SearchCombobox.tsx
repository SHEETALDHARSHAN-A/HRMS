// src/components/common/SearchCombobox.tsx

import { Fragment, useState } from 'react';
import { Combobox, Transition } from '@headlessui/react';
import { Check, ChevronsUpDown, X } from 'lucide-react';

interface SearchComboboxProps {
  label: string;
  placeholder: string;
  options: string[];
  selected: string[];
  onChange: (value: string[]) => void;
  // We add className to allow tailwind styling from the parent
  className?: string; 
}

/**
 * A reusable multi-select combobox for search filters,
 * built with Headless UI, Tailwind CSS, and Lucide-React.
 */
export const SearchCombobox = ({
  label,
  placeholder,
  options,
  selected,
  onChange,
  className = '', // Default to empty string
}: SearchComboboxProps) => {
  const [query, setQuery] = useState('');

  // Filter options based on user's query
  const filteredOptions =
    query === ''
      ? options
      : options.filter((option) =>
          option
            .toLowerCase()
            .replace(/\s+/g, '')
            .includes(query.toLowerCase().replace(/\s+/g, ''))
        );

  // Handle removing a selected item
  const handleRemove = (option: string) => {
    onChange(selected.filter((item) => item !== option));
  };

  return (
    <div className={`w-full ${className}`}>
      <Combobox value={selected} onChange={onChange} multiple>
        {/* Label */}
        <Combobox.Label className="block text-sm font-medium leading-6 text-gray-900">
          {label}
        </Combobox.Label>
        
        {/* Input and Button */}
        <div className="relative mt-2">
          <Combobox.Input
            className="w-full rounded-md border-0 bg-white py-2 pl-3 pr-10 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-[var(--color-primary-500)] sm:text-sm sm:leading-6"
            placeholder={placeholder}
            onChange={(event) => setQuery(event.target.value)}
            onBlur={() => setQuery('')}
            // We use tags below, so the input itself is just for querying
            displayValue={() => ''} 
          />
          <Combobox.Button className="absolute inset-y-0 right-0 flex items-center rounded-r-md px-2 focus:outline-none">
            <ChevronsUpDown
              className="h-5 w-5 text-gray-400"
              aria-hidden="true"
            />
          </Combobox.Button>
        </div>

        {/* Selected item tags */}
        {selected.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {selected.map((option) => (
              <span
                key={option}
                className="inline-flex items-center gap-x-1.5 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-800"
              >
                {option}
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault(); // Prevent form submission
                    handleRemove(option);
                  }}
                  className="group relative -mr-1 h-3.5 w-3.5 rounded-sm hover:bg-blue-600/20"
                >
                  <span className="sr-only">Remove</span>
                  <X
                    className="h-3.5 w-3.5 text-blue-700 stroke-current"
                    aria-hidden="true"
                  />
                  <span className="absolute -inset-1" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Options Popup */}
        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
          afterLeave={() => setQuery('')}
        >
          {/* We set a high z-index (z-50) to appear over the layout content */}
          <Combobox.Options className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
            {filteredOptions.length === 0 && query !== '' ? (
              <div className="relative cursor-default select-none px-4 py-2 text-gray-700">
                Nothing found.
              </div>
            ) : (
              filteredOptions.map((option) => (
                <Combobox.Option
                  key={option}
                  className={({ active }) =>
                    `relative cursor-default select-none py-2 pl-10 pr-4 ${
                      active ? 'bg-[var(--color-primary-500)] text-white' : 'text-gray-900'
                    }`
                  }
                  value={option}
                >
                  {({ selected, active }) => (
                    <>
                      <span
                        className={`block truncate ${
                          selected ? 'font-medium' : 'font-normal'
                        }`}
                      >
                        {option}
                      </span>
                      {selected ? (
                        <span
                          className={`absolute inset-y-0 left-0 flex items-center pl-3 ${
                            active ? 'text-white' : 'text-[var(--color-primary-600)]'
                          }`}
                        >
                          <Check className="h-5 w-5" aria-hidden="true" />
                        </span>
                      ) : null}
                    </>
                  )}
                </Combobox.Option>
              ))
            )}
          </Combobox.Options>
        </Transition>
      </Combobox>
    </div>
  );
};

export default SearchCombobox;