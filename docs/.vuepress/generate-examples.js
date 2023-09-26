const fs = require('fs');
const path = require('path');


function extractDescriptionFromPythonCode(code) {
  const match = code.match(/(['"]{3}[\s\S]*?['"]{3})/);

  if (match) {
    return match[0].replace(/['"]{3}/g, '').trim();
  } else {
    return '';
  }
}

function removeExtraLineBreaksFromCodeBlock(code) {
  return code.replace(/(\r?\n){3,}/g, '\n\n').trim();
}


function removeCommentsFromPythonCode(code) {
  return code.replace(/(^['"]{3}[\s\S]*?['"]{3})/gm, '').trim();
}


function convertToMarkdown(filePath, outputDirectory) {
  try {
    const pythonCode = fs.readFileSync(filePath, 'utf8');
    const description = extractDescriptionFromPythonCode(pythonCode);
    const codeWithoutComments = removeCommentsFromPythonCode(pythonCode);
    const codeWithoutExtraLineBreaks = removeExtraLineBreaksFromCodeBlock(codeWithoutComments);
    const fileName = path.basename(filePath, '.py');
    const markdownFileName = fileName + '.md';
    const markdownFilePath = path.join(outputDirectory, markdownFileName);
    const title = fileName.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
    const markdownContent = `# ${title}\n\n${description}\n\n\`\`\`python\n${codeWithoutExtraLineBreaks}\n\`\`\``;
    fs.writeFileSync(markdownFilePath, markdownContent);
    console.log(`Converted ${filePath} to ${markdownFilePath}`);
  } catch (error) {
    console.error(`Error converting ${filePath}: ${error.message}`);
  }
}

function generateExamples(directoryPath, outputDirectory) {
  if (!fs.existsSync(outputDirectory)) {
    fs.mkdirSync(outputDirectory);
  }

  fs.readdirSync(directoryPath).forEach(file => {
    const filePath = path.join(directoryPath, file);

    if (file.endsWith('.py')) {
      convertToMarkdown(filePath, outputDirectory);
    }
  });
}


module.exports = {
  generateExamples
}


