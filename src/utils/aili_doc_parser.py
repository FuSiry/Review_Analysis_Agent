#!/usr/bin/env python3
import time

from alibabacloud_docmind_api20220711 import models as docmind_api20220711_models
from alibabacloud_docmind_api20220711.client import Client as docmind_api20220711Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models


class DocParser:
    def __init__(self, endpoint="docmind-api.cn-hangzhou.aliyuncs.com"):
        """
        初始化文档解析器

        Args:
            endpoint (str): API端点地址
        """
        self.endpoint = endpoint
        self.client = self._init_client()

    def _init_client(self):
        """
        初始化API客户端

        Returns:
            docmind_api20220711Client: API客户端实例
        """
        config = open_api_models.Config(
            # 通过credentials获取配置中的AccessKey ID
            access_key_id=get_config_section("alicloud", "access_key"),
            # 通过credentials获取配置中的AccessKey Secret
            access_key_secret=get_config_section("alicloud", "access_secret")
        )
        # 设置访问的域名
        config.endpoint = self.endpoint
        return docmind_api20220711Client(config)

    def submit_job(self, file_path, file_name=None):
        """
        提交文档解析任务

        Args:
            file_path (str): 本地文件路径
            file_name (str, optional): 文件名

        Returns:
            str: 任务ID，如果失败则返回None
        """
        try:
            # 如果未指定文件名，则从文件路径中提取
            if not file_name:
                file_name = file_path.split('/')[-1]

            # 构造请求对象
            # 是否启用VLM增强，enhancement=False 关闭
            request = docmind_api20220711_models.SubmitDocParserJobAdvanceRequest(
                file_url_object=open(file_path, "rb"),
                file_name=file_name,
                file_name_extension=file_name.split('.')[-1] if '.' in file_name else None,
                llm_enhancement=True,
                enhancement_mode="VLM",
            )

            runtime = util_models.RuntimeOptions()

            # 提交任务
            response = self.client.submit_doc_parser_job_advance(request, runtime)
            task_id = response.body.data.id

            print(f"任务已提交，任务ID: {task_id}")
            return task_id
        except Exception as error:
            print(f"提交任务时出错: {error}")
            return None

    def query_status(self, task_id):
        """
        查询任务状态

        Args:
            task_id (str): 任务ID

        Returns:
            dict: 任务状态信息，如果失败则返回None
        """
        try:
            request = docmind_api20220711_models.QueryDocParserStatusRequest(id=task_id)
            response = self.client.query_doc_parser_status(request)
            return response.body.data.to_map() if response.body.data else None
        except Exception as error:
            print(f"查询任务状态时出错: {error}")
            return None

    def get_result(self, task_id, layout_num=0, layout_step_size=10):
        """
        获取文档解析结果（支持增量获取）

        Args:
            task_id (str): 任务ID
            layout_num (int): 起始布局编号
            layout_step_size (int): 步长

        Returns:
            dict: 解析结果，如果失败则返回None
        """
        try:
            request = docmind_api20220711_models.GetDocParserResultRequest(
                id=task_id,
                layout_step_size=layout_step_size,
                layout_num=layout_num
            )
            response = self.client.get_doc_parser_result(request)
            return response.body.data if response.body.data else None
        except Exception as error:
            print(f"获取解析结果时出错: {error}")
            return None

    def wait_for_completion(self, task_id, poll_interval=5):
        """
        等待任务完成

        Args:
            task_id (str): 任务ID
            poll_interval (int): 轮询间隔（秒）

        Returns:
            bool: 任务是否成功完成
        """
        print("开始轮询任务状态...")
        while True:
            status_data = self.query_status(task_id)
            if not status_data:
                return False
            print(status_data)
            status = status_data.get('Status', '').lower()

            # 检查任务是否完成
            if status == 'success':
                print("任务已成功完成")
                return True
            elif status == 'failed':
                print("任务执行失败")
                return False
            else:
                # 任务仍在处理中
                print(".")
                time.sleep(poll_interval)

    def collect_results_incrementally(self, task_id, layout_step_size=10):
        """
        增量收集解析结果

        Args:
            task_id (str): 任务ID
            layout_step_size (int): 步长

        Yields:
            list: 每次获取到的布局块列表
        """
        layout_num = 0
        while True:
            result_data = self.get_result(task_id, layout_num, layout_step_size)
            if not result_data:
                break
            layouts = result_data.get('layouts', [])
            if not layouts:
                break

            yield layouts

            # 更新下次获取的起始位置
            layout_num += len(layouts)

            # 如果获取到的数量小于步长，说明已经获取完所有内容
            if len(layouts) < layout_step_size:
                break

    def table_to_html(self, table_layout):
        """
        将表格布局转换为HTML格式

        Args:
            table_layout (dict): 表格布局数据

        Returns:
            str: HTML格式的表格
        """
        cells = table_layout.get('cells', [])
        if not cells:
            return ""

        # 创建HTML表格
        html_parts = ['<table border="1" cellspacing="0" cellpadding="2">']

        # 用于跟踪哪些单元格已被处理（处理跨行跨列的情况）
        processed_cells = set()

        # 按行分组单元格
        rows = {}
        for cell in cells:
            row_start = cell.get('ysc', 0)
            if row_start not in rows:
                rows[row_start] = []
            rows[row_start].append(cell)

        # 按行顺序处理
        for row_idx in sorted(rows.keys()):
            html_parts.append('<tr>')
            # 按列顺序排序
            row_cells = sorted(rows[row_idx], key=lambda x: x.get('xsc', 0))

            for cell in row_cells:
                cell_key = (cell.get('ysc', 0), cell.get('xsc', 0))
                if cell_key in processed_cells:
                    continue

                # 计算跨行跨列
                rowspan = cell.get('yec', 0) - cell.get('ysc', 0) + 1
                colspan = cell.get('xec', 0) - cell.get('xsc', 0) + 1

                # 标记已处理的单元格
                for i in range(rowspan):
                    for j in range(colspan):
                        processed_cells.add((cell.get('ysc', 0) + i, cell.get('xsc', 0) + j))

                # 获取单元格文本内容
                cell_text = ""
                cell_layouts = cell.get('layouts', [])
                for layout in cell_layouts:
                    if 'text' in layout:
                        cell_text += layout['text']

                # 清理文本内容
                cell_text = cell_text.strip().replace('\n', '<br>')

                # 添加单元格HTML
                cell_attrs = []
                if rowspan > 1:
                    cell_attrs.append(f'rowspan="{rowspan}"')
                if colspan > 1:
                    cell_attrs.append(f'colspan="{colspan}"')

                html_parts.append(f'<td {" ".join(cell_attrs)}>{cell_text}</td>')

            html_parts.append('</tr>')

        html_parts.append('</table>')
        return ''.join(html_parts)

    def generate_markdown(self, layouts):
        """
        将布局块转换为Markdown内容

        Args:
            layouts (list): 布局块列表

        Returns:
            str: Markdown内容
        """
        markdown_content = ""
        for layout in layouts:
            # 直接使用返回的markdownContent字段
            if layout.get('type')=="table":
                # 对于表格类型，转换为HTML格式
                table_html = self.table_to_html(layout)
                markdown_content += table_html + "\n\n"
            else:
                markdown_content += layout.get('markdownContent', '') + "\n"
        return markdown_content

    def process_document(self, file_path, output_path, layout_step_size=10, poll_interval=5):
        """
        处理整个文档：提交、轮询、增量获取结果并生成Markdown文件

        Args:
            file_path (str): 本地文件路径
            output_path (str): 输出Markdown文件路径
            layout_step_size (int): 增量获取步长
            poll_interval (int): 轮询间隔（秒）

        Returns:
            bool: 是否成功处理
        """
        # 1. 提交任务
        print("正在提交文档解析任务...")
        task_id = self.submit_job(file_path)
        if not task_id:
            print("提交任务失败")
            return False

        # 2. 等待任务完成
        if not self.wait_for_completion(task_id, poll_interval):
            print("任务未成功完成")
            return False

        # 3. 增量获取结果并写入文件
        print("任务已完成，开始获取解析结果...")
        with open(output_path, 'w', encoding='utf-8') as f:

            # 增量获取并写入内容
            for layouts in self.collect_results_incrementally(task_id, layout_step_size):
                markdown_content = self.generate_markdown(layouts)
                f.write(markdown_content)
                f.flush()  # 立即刷新到文件
        print(f"文档解析完成，结果已保存至: {output_path}")
        return True

def main():
    input_file = "../../tests/pdf/PRD.pdf"
    output_file = "../../tests/pdf/PRD.md"
    step_size = 10
    poll_interval = 5
   
    # 创建文档解析器实例
    parser = DocParser()

    # 处理文档
    success = parser.process_document(
        input_file,
        output_file,
        layout_step_size=step_size,
        poll_interval=poll_interval
    )

    if success:
        print("文档处理成功完成！")
    else:
        print("文档处理失败！")
        exit(1)

if __name__ == "__main__":
    main()
