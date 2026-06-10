import React from 'react';

import VeryHappy from '../../assets/VeryHappy.png';
import Happy from '../../assets/Happy.png';
import Neutral from '../../assets/Neutral.png';
import Sad from '../../assets/Sad.png';
import VerySad from '../../assets/VerySad.png';

interface FeelingSelectorProps {
  onSelectFeeling: (feeling: string) => void;
}

const feelings = [
  { name: 'Very Happy', image: VeryHappy },
  { name: 'Happy', image: Happy },
  { name: 'Neutral', image: Neutral },
  { name: 'Sad', image: Sad },
  { name: 'Very Sad', image: VerySad },
];

export const FeelingSelector: React.FC<FeelingSelectorProps> = ({ onSelectFeeling }) => {
  return (
    <div className="feeling-selector">
      {feelings.map(({ name, image }) => (
        <div 
          key={name} 
          className="feeling-option" 
          onClick={() => onSelectFeeling(name)}
        >
          <img src={image} alt={name} />
          <span>{name}</span>
        </div>
      ))}
    </div>
  );
}; 