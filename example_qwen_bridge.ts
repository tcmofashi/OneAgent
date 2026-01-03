/**
 * 示例 TypeScript 文件 - 展示 Qwen Bridge Agent 的编码能力
 * 
 * 这个文件展示了 Qwen Code CLI 如何与 OneAgent 框架集成工作。
 * 它包含了一个简单的函数，用于处理任务并返回结果。
 */

// 定义任务接口
interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high';
}

// 定义任务执行结果接口
interface TaskResult {
  taskId: string;
  status: string;
  result: string;
  timestamp: Date;
}

/**
 * 处理任务并返回结果
 * @param task - 要处理的任务对象
 * @returns 任务执行结果
 */
function executeTask(task: Task): TaskResult {
  console.log(`开始处理任务: ${task.title}`);
  console.log(`任务描述: ${task.description}`);
  
  // 模拟任务处理逻辑
  let result: string;
  switch (task.priority) {
    case 'high':
      result = `高优先级任务 ${task.id} 已紧急处理完成`;
      break;
    case 'medium':
      result = `中优先级任务 ${task.id} 已正常处理完成`;
      break;
    case 'low':
      result = `低优先级任务 ${task.id} 已处理完成`;
      break;
    default:
      result = `任务 ${task.id} 处理完成`;
  }
  
  return {
    taskId: task.id,
    status: 'completed',
    result: result,
    timestamp: new Date()
  };
}

/**
 * 批量处理任务
 * @param tasks - 任务数组
 * @returns 所有任务的执行结果
 */
function batchExecuteTasks(tasks: Task[]): TaskResult[] {
  return tasks.map(task => executeTask(task));
}

/**
 * 格式化任务结果输出
 * @param results - 任务结果数组
 * @returns 格式化的字符串
 */
function formatTaskResults(results: TaskResult[]): string {
  let output = '任务执行结果汇总:\n';
  output += '='.repeat(50) + '\n';
  
  results.forEach((result, index) => {
    output += `${index + 1}. 任务ID: ${result.taskId}\n`;
    output += `   状态: ${result.status}\n`;
    output += `   结果: ${result.result}\n`;
    output += `   时间: ${result.timestamp.toLocaleString()}\n`;
    output += '-'.repeat(50) + '\n';
  });
  
  output += `总计处理了 ${results.length} 个任务\n`;
  return output;
}

// 示例使用
const sampleTasks: Task[] = [
  {
    id: 'TASK-001',
    title: '初始化系统',
    description: '启动并初始化 OneAgent 系统',
    status: 'pending',
    priority: 'high'
  },
  {
    id: 'TASK-002',
    title: '加载配置',
    description: '加载并验证配置文件',
    status: 'pending',
    priority: 'medium'
  },
  {
    id: 'TASK-003',
    title: '注册工具',
    description: '注册所有可用工具和代理',
    status: 'pending',
    priority: 'medium'
  },
  {
    id: 'TASK-004',
    title: '生成报告',
    description: '生成系统状态报告',
    status: 'pending',
    priority: 'low'
  }
];

// 执行示例任务
console.log('Qwen Bridge Agent 示例代码执行开始...\n');
const results = batchExecuteTasks(sampleTasks);
console.log(formatTaskResults(results));
console.log('示例代码执行完成！');

// 导出函数供其他模块使用
export {
  Task,
  TaskResult,
  executeTask,
  batchExecuteTasks,
  formatTaskResults
};